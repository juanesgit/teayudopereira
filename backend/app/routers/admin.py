"""
Endpoints de administración — solo coordinadores.
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


def _require_coordinator(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.coordinator:
        raise HTTPException(status_code=403, detail="Solo coordinadores pueden acceder")
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
    current_user: User = Depends(_require_coordinator),
):
    """Envía SMS a una lista de números específicos."""
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
    current_user: User = Depends(_require_coordinator),
):
    """Envía SMS masivo a todos los voluntarios y/o coordinadores activos."""
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


@router.get("/volunteers")
async def list_volunteers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(_require_coordinator),
):
    """Lista voluntarios y coordinadores con sus datos de contacto."""
    result = await db.execute(
        select(User).where(
            User.role.in_([UserRole.volunteer, UserRole.coordinator]),
            User.is_active == True,  # noqa: E712
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
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]
