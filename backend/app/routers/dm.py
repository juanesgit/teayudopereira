"""
Mensajes directos (DM) — voluntario/coordinador/víctima ↔ admin.

Sala: "dm_{min(uid_a, uid_admin)}_{max(uid_a, uid_admin)}"
WS:  /ws/dm/{room}?token=<jwt>
REST admin:
  GET  /dm/rooms          → lista de salas con último mensaje y no leídos
  GET  /dm/rooms/{room}   → historial de la sala
  POST /dm/rooms/{room}/read → marcar mensajes como leídos
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from jose import JWTError, jwt

from app.config import settings
from app.database import AsyncSessionLocal, get_db
from app.models.chat import ChatMessage
from app.models.guest_session import GuestSession
from app.models.user import User, UserRole
from app.services.auth import get_current_user
from app.routers.push import send_push_to_user, send_push_to_admins, send_push_to_guest

log = logging.getLogger(__name__)
router = APIRouter(tags=["DMs"])

HISTORY_LIMIT = 60
ALLOWED_ROLES = {"volunteer", "coordinator", "admin", "victim"}

# ─── Connection manager por sala ─────────────────────────────────────────────

class DmManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, Dict[WebSocket, dict]] = {}

    def _room(self, room: str) -> Dict[WebSocket, dict]:
        return self._rooms.setdefault(room, {})

    async def connect(self, ws: WebSocket, room: str, user_id: int, name: str, role: str) -> None:
        await ws.accept()
        self._room(room)[ws] = {"user_id": user_id, "name": name, "role": role}

    def disconnect(self, ws: WebSocket, room: str) -> None:
        self._room(room).pop(ws, None)
        if not self._room(room):
            self._rooms.pop(room, None)

    async def broadcast(self, room: str, payload: dict) -> None:
        dead: List[WebSocket] = []
        for ws in list(self._room(room)):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._room(room).pop(ws, None)

dm_manager = DmManager()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def _make_room(uid_a: int, uid_b: int) -> str:
    return f"dm_{min(uid_a, uid_b)}_{max(uid_a, uid_b)}"

def _msg_payload(msg: ChatMessage) -> dict:
    return {
        "id": msg.id,
        "channel": msg.channel,
        "user_id": msg.user_id,
        "sender_name": msg.sender_name,
        "sender_role": msg.sender_role,
        "text": msg.text,
        "is_read": msg.is_read,
        "is_system": msg.is_system,
        "created_at": msg.created_at.isoformat() + "Z",
    }

async def _get_history(db: AsyncSession, room: str) -> list:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.channel == room)
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    msgs = list(reversed(result.scalars().all()))
    return [_msg_payload(m) for m in msgs]

async def _persist(db: AsyncSession, channel: str, **kwargs) -> ChatMessage:
    msg = ChatMessage(channel=channel, **kwargs)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/ws/dm/{room}")
async def dm_ws(ws: WebSocket, room: str, token: str = Query(...)):
    # Validar JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except (JWTError, Exception):
        await ws.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user: Optional[User] = (await db.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()

    if not user or not user.is_active:
        await ws.close(code=1008)
        return

    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if user_role not in ALLOWED_ROLES:
        await ws.close(code=1008)
        return

    # Verificar que el usuario pertenece a esta sala
    # Salas guest_* solo admins/coordinadores pueden unirse vía JWT
    if room.startswith("guest_"):
        if user_role not in ("admin", "coordinator"):
            await ws.close(code=1008)
            return
    else:
        parts = room.replace("dm_", "").split("_")
        if len(parts) != 2 or str(user_id) not in parts:
            await ws.close(code=1008)
            return

    name = f"{user.full_name}" + (f" {user.last_name}" if user.last_name else "")

    await dm_manager.connect(ws, room, user_id, name, user_role)

    # Historial + marcar leídos
    async with AsyncSessionLocal() as db:
        history = await _get_history(db, room)
        # Marcar como leídos los mensajes del otro
        await db.execute(
            update(ChatMessage)
            .where(ChatMessage.channel == room, ChatMessage.user_id != user_id, ChatMessage.is_read == False)  # noqa
            .values(is_read=True)
        )
        await db.commit()

    await ws.send_json({"type": "history", "data": history})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                text = str(json.loads(raw).get("text", "")).strip()[:500]
            except Exception:
                text = raw.strip()[:500]

            if not text:
                continue

            async with AsyncSessionLocal() as db:
                msg = await _persist(
                    db, channel=room,
                    user_id=user_id, sender_name=name, sender_role=user_role,
                    text=text, is_system=False, is_read=False,
                    created_at=datetime.utcnow(),
                )
                # Push al otro participante si no está conectado al WS
                room_conns = dm_manager._rooms.get(room, {})
                if room.startswith("guest_"):
                    # Admin respondiendo a ciudadano → push al guest
                    guest_in_room = any(
                        info["role"] == "victim" for info in room_conns.values()
                    )
                    if not guest_in_room:
                        gs = (await db.execute(
                            select(GuestSession).where(GuestSession.room == room)
                        )).scalar_one_or_none()
                        if gs:
                            await send_push_to_guest(
                                db, gs.guest_token, f"💬 Coordinación", text[:80], "/"
                            )
                else:
                    other_connected = any(
                        info["user_id"] != user_id for info in room_conns.values()
                    )
                    if not other_connected:
                        parts = room.replace("dm_", "").split("_")
                        other_id = int(parts[0]) if int(parts[1]) == user_id else int(parts[1])
                        if user_role in ("admin", "coordinator"):
                            await send_push_to_user(db, other_id, f"💬 {name}", text[:80], "/")
                        else:
                            await send_push_to_admins(db, f"💬 {name}", text[:80], "/")
            await dm_manager.broadcast(room, {"type": "message", "data": _msg_payload(msg)})

    except WebSocketDisconnect:
        dm_manager.disconnect(ws, room)
    except Exception as exc:
        log.error("DM WS error: %s", exc)
        dm_manager.disconnect(ws, room)

# ─── REST — Admin ─────────────────────────────────────────────────────────────

@router.get("/dm/rooms")
async def list_dm_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin: lista todas las salas DM con último mensaje y no leídos."""
    if current_user.role not in (UserRole.admin, UserRole.coordinator):
        raise HTTPException(403, "Sin permisos")

    # ── Salas DM regulares (voluntarios/coordinadores) ────────────────────
    result = await db.execute(
        select(ChatMessage.channel)
        .where(ChatMessage.channel.like("dm_%"))
        .where(ChatMessage.channel.contains(f"_{current_user.id}_") |
               ChatMessage.channel.like(f"dm_{current_user.id}_%") |
               ChatMessage.channel.like(f"%_{current_user.id}"))
        .distinct()
    )
    dm_rooms = [r[0] for r in result.fetchall()]

    # ── Salas guest (ciudadanos anónimos) ─────────────────────────────────
    guest_result = await db.execute(
        select(ChatMessage.channel)
        .where(ChatMessage.channel.like("guest_%"))
        .distinct()
    )
    guest_rooms = [r[0] for r in guest_result.fetchall()]

    out = []

    # Procesar salas DM normales
    for room in dm_rooms:
        last = (await db.execute(
            select(ChatMessage)
            .where(ChatMessage.channel == room)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        unread = (await db.execute(
            select(func.count()).where(
                ChatMessage.channel == room,
                ChatMessage.user_id != current_user.id,
                ChatMessage.is_read == False  # noqa
            )
        )).scalar()

        parts = room.replace("dm_", "").split("_")
        other_id = int(parts[0]) if int(parts[1]) == current_user.id else int(parts[1])
        other = (await db.execute(select(User).where(User.id == other_id))).scalar_one_or_none()

        out.append({
            "room": room,
            "other_id": other_id,
            "other_name": f"{other.full_name}{' '+other.last_name if other and other.last_name else ''}" if other else "Desconocido",
            "other_role": other.role.value if other and hasattr(other.role, "value") else "unknown",
            "last_message": _msg_payload(last) if last else None,
            "unread": unread,
            "is_guest": False,
        })

    # Procesar salas guest
    for room in guest_rooms:
        gs = (await db.execute(
            select(GuestSession).where(GuestSession.room == room)
        )).scalar_one_or_none()

        last = (await db.execute(
            select(ChatMessage)
            .where(ChatMessage.channel == room)
            .order_by(ChatMessage.created_at.desc())
            .limit(1)
        )).scalar_one_or_none()

        unread = (await db.execute(
            select(func.count()).where(
                ChatMessage.channel == room,
                ChatMessage.sender_role == "victim",
                ChatMessage.is_read == False  # noqa
            )
        )).scalar()

        guest_name = gs.guest_name if gs else "Ciudadano"
        report_id = gs.report_id if gs else None

        out.append({
            "room": room,
            "other_id": None,
            "other_name": guest_name,
            "other_role": "victim",
            "last_message": _msg_payload(last) if last else None,
            "unread": unread,
            "is_guest": True,
            "report_id": report_id,
        })

    out.sort(key=lambda x: x["last_message"]["created_at"] if x["last_message"] else "", reverse=True)
    return out


@router.get("/dm/rooms/{room}")
async def get_dm_room(
    room: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Historial de una sala DM. Solo participantes o admin para guest rooms."""
    user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
    if room.startswith("guest_"):
        if user_role not in ("admin", "coordinator"):
            raise HTTPException(403, "Sin acceso")
    else:
        parts = room.replace("dm_", "").split("_")
        if len(parts) != 2 or str(current_user.id) not in parts:
            raise HTTPException(403, "Sin acceso")

    # Marcar como leídos
    await db.execute(
        update(ChatMessage)
        .where(ChatMessage.channel == room, ChatMessage.user_id != current_user.id, ChatMessage.is_read == False)  # noqa
        .values(is_read=True)
    )
    await db.commit()

    return await _get_history(db, room)


@router.get("/dm/my-room")
async def my_dm_room(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Devuelve el room_id del DM entre el usuario actual y el admin principal."""
    # Buscar el primer admin activo
    admin = (await db.execute(
        select(User).where(User.role == UserRole.admin, User.is_active == True)  # noqa
        .limit(1)
    )).scalar_one_or_none()

    if not admin:
        raise HTTPException(404, "No hay admin disponible")

    return {"room": _make_room(current_user.id, admin.id), "admin_id": admin.id}
