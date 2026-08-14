from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.danger_zone import DangerZone, DangerLevel
from app.models.user import User, UserRole
from app.schemas.danger_zone import DangerZoneCreate, DangerZoneUpdate, DangerZoneOut
from app.services.auth import get_current_user, get_current_user_optional
from app.services import sms

router = APIRouter(prefix="/danger-zones", tags=["Zonas de peligro"])


async def _notify_danger_zone(zone: DangerZone, db: AsyncSession) -> None:
    """Notifica por SMS a voluntarios/coordinadores cuando la zona es de nivel alto o crítico."""
    if zone.danger_level not in (DangerLevel.high, DangerLevel.critical):
        return
    try:
        result = await db.execute(
            select(User).where(
                User.role.in_([UserRole.volunteer, UserRole.coordinator]),
                User.is_active == True,  # noqa: E712
                User.phone != None,  # noqa: E711
            )
        )
        volunteers = result.scalars().all()
        phones = [v.phone for v in volunteers if v.phone]
        if not phones:
            return
        address = zone.address or f"({zone.lat:.4f}, {zone.lng:.4f})"
        message = sms.msg_zona_peligro(zone.name, zone.danger_level.value, address)
        await sms.send_sms(phones, message)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Error notificando zona de peligro: %s", exc)


@router.post("/", response_model=DangerZoneOut, status_code=201)
async def create_danger_zone(
    data: DangerZoneCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Cualquier persona puede reportar una zona de peligro."""
    zone = DangerZone(**data.model_dump(), created_by=current_user.id if current_user else None)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    # Alertar por SMS si el nivel es alto o crítico
    background_tasks.add_task(_notify_danger_zone, zone, db)
    return zone


@router.get("/", response_model=List[DangerZoneOut])
async def list_danger_zones(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(DangerZone)
    if active_only:
        query = query.where(DangerZone.is_active == True)  # noqa: E712
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/admin/all", response_model=List[DangerZoneOut])
async def list_all_danger_zones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin: lista todas las zonas incluidas las inactivas."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Solo administradores")
    result = await db.execute(select(DangerZone).order_by(DangerZone.created_at.desc()))
    return result.scalars().all()


@router.patch("/{zone_id}", response_model=DangerZoneOut)
async def update_danger_zone(
    zone_id: int,
    data: DangerZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.admin, UserRole.coordinator, UserRole.volunteer):
        raise HTTPException(status_code=403, detail="Sin permisos")

    result = await db.execute(select(DangerZone).where(DangerZone.id == zone_id))
    zone = result.scalar_one_or_none()
    if not zone:
        raise HTTPException(status_code=404, detail="Zona no encontrada")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(zone, field, value)

    await db.commit()
    await db.refresh(zone)
    return zone
