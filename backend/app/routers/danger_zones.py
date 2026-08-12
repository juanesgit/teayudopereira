from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.danger_zone import DangerZone
from app.models.user import User, UserRole
from app.schemas.danger_zone import DangerZoneCreate, DangerZoneUpdate, DangerZoneOut
from app.services.auth import get_current_user, get_current_user_optional

router = APIRouter(prefix="/danger-zones", tags=["Zonas de peligro"])


@router.post("/", response_model=DangerZoneOut, status_code=201)
async def create_danger_zone(
    data: DangerZoneCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Cualquier persona puede reportar una zona de peligro."""
    zone = DangerZone(**data.model_dump(), created_by=current_user.id if current_user else None)
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
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


@router.patch("/{zone_id}", response_model=DangerZoneOut)
async def update_danger_zone(
    zone_id: int,
    data: DangerZoneUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in (UserRole.coordinator, UserRole.volunteer):
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
