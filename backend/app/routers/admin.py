"""
Endpoints de administración — solo rol admin.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models.user import User, UserRole
from app.services.auth import get_current_user
from app.services import sms

router = APIRouter(prefix="/admin", tags=["Administración"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Solo admin del sistema."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Solo administradores del sistema pueden acceder")
    return current_user


def _require_staff(current_user: User = Depends(get_current_user)) -> User:
    """Coordinadores Y admin del sistema."""
    if current_user.role not in (UserRole.coordinator, UserRole.admin):
        raise HTTPException(status_code=403, detail="Se requiere rol coordinador o admin")
    return current_user


# ─── Schemas ─────────────────────────────────────────────────────────────────

class SmsSendRequest(BaseModel):
    phones: List[str]          # números directos
    message: str


class SmsBroadcastRequest(BaseModel):
    message: str
    target: str = "all"        # "all" | "volunteers" | "coordinators"


class SmsSendResponse(BaseModel):
    ok: bool
    recipients: int
    message: str


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/sms/send", response_model=SmsSendResponse)
async def sms_send_direct(
    data: SmsSendRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(_require_staff),
):
    """Envía SMS a una lista de números específicos. Coordinadores y admin."""
    if not data.phones:
        raise HTTPException(status_code=400, detail="Debes indicar al menos un número")
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    background_tasks.add_task(sms.send_sms, data.phones, data.message.strip())
    return SmsSendResponse(ok=True, recipients=len(data.phones), message="SMS en envío")


@router.post("/sms/broadcast", response_model=SmsSendResponse)
async def sms_broadcast(
    data: SmsBroadcastRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_staff),
):
    """Envía SMS masivo. Coordinadores y admin."""
    if not data.message.strip():
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")

    query = select(User).where(User.is_active == True)  # noqa: E712
    if data.target == "volunteers":
        query = query.where(User.role == UserRole.volunteer)
    elif data.target == "coordinators":
        query = query.where(User.role == UserRole.coordinator)
    else:  # "all"
        query = query.where(User.role.in_([UserRole.volunteer, UserRole.coordinator]))

    result = await db.execute(query)
    users = result.scalars().all()
    phones = [u.phone for u in users if u.phone]

    if not phones:
        return SmsSendResponse(ok=False, recipients=0, message="Sin destinatarios con teléfono")

    background_tasks.add_task(sms.send_sms, phones, data.message.strip())
    return SmsSendResponse(ok=True, recipients=len(phones), message=f"Broadcast a {len(phones)} número(s) en envío")


@router.get("/sms/balance")
async def sms_balance(current_user: User = Depends(_require_admin)):
    """Consulta saldo de créditos SMS."""
    data = await sms.get_balance()
    if data is None:
        raise HTTPException(status_code=503, detail="No se pudo consultar el saldo")
    return data


@router.get("/sms/history")
async def sms_history(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(_require_admin),
):
    """Historial de SMS enviados."""
    data = await sms.get_history(limit=limit, offset=offset)
    if data is None:
        raise HTTPException(status_code=503, detail="No se pudo consultar el historial")
    return data


@router.get("/volunteers")
async def list_volunteers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    """Lista todos los usuarios excepto víctimas."""
    result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.volunteer, UserRole.coordinator, UserRole.admin]),
        ).order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "full_name": u.full_name,
            "last_name": u.last_name or "",
            "role": u.role,
            "phone": u.phone,
            "neighborhood": u.neighborhood or "",
            "skills": u.skills or "",
            "is_active": u.is_active,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


class UserPatchRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None


@router.patch("/users/{user_id}")
async def patch_user(
    user_id: int,
    data: UserPatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    """Cambia el rol o activa/desactiva un usuario."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="No puedes modificarte a ti mismo")

    if data.role is not None:
        try:
            user.role = UserRole(data.role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Rol inválido: {data.role}")

    if data.is_active is not None:
        user.is_active = data.is_active

    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "role": user.role, "is_active": user.is_active}


@router.get("/stats")
async def system_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    """Estadísticas globales del sistema."""
    from app.models.report import Report, ReportStatus
    from app.models.danger_zone import DangerZone
    from sqlalchemy import func

    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_volunteers = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.volunteer)
    )).scalar()
    total_coordinators = (await db.execute(
        select(func.count(User.id)).where(User.role == UserRole.coordinator)
    )).scalar()
    total_reports = (await db.execute(select(func.count(Report.id)))).scalar()
    pending_reports = (await db.execute(
        select(func.count(Report.id)).where(Report.status == ReportStatus.pending)
    )).scalar()
    resolved_reports = (await db.execute(
        select(func.count(Report.id)).where(Report.status == ReportStatus.resolved)
    )).scalar()
    danger_zones = (await db.execute(
        select(func.count(DangerZone.id)).where(DangerZone.is_active == True)  # noqa: E712
    )).scalar()

    return {
        "users": {"total": total_users, "volunteers": total_volunteers, "coordinators": total_coordinators},
        "reports": {"total": total_reports, "pending": pending_reports, "resolved": resolved_reports},
        "danger_zones": danger_zones,
    }
