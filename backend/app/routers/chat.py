"""
WebSocket chat — canal grupal para voluntarios, coordinadores y admins.

Flujo:
  1. Cliente abre WS a /ws/chat?token=<jwt>
  2. Se valida el token; si falla se cierra con 1008.
  3. Al conectar se envían los últimos N mensajes (historial).
  4. Cada mensaje recibido se persiste y se retransmite a todos los conectados.
  5. Mensajes de sistema se pueden publicar llamando a broadcast_system_message()
     desde otros routers (reportes, zonas de peligro, etc.).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jose import JWTError, jwt

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.chat import ChatMessage
from app.models.user import User
from app.services.broadcaster import group_broadcaster as manager

log = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])

# ─── Helpers ──────────────────────────────────────────────────────────────────

HISTORY_LIMIT = 60  # últimos mensajes al conectar

def _msg_payload(msg: ChatMessage) -> dict:
    return {
        "id": msg.id,
        "user_id": msg.user_id,
        "sender_name": msg.sender_name,
        "sender_role": msg.sender_role,
        "text": msg.text,
        "is_system": msg.is_system,
        "created_at": msg.created_at.isoformat() + "Z",
    }


async def _get_history(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.channel == "group")
        .order_by(ChatMessage.created_at.desc())
        .limit(HISTORY_LIMIT)
    )
    msgs = list(reversed(result.scalars().all()))
    return [_msg_payload(m) for m in msgs]


async def _persist(db: AsyncSession, **kwargs) -> ChatMessage:
    msg = ChatMessage(**kwargs)
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg


# ─── Public helper — llamado desde otros routers ──────────────────────────────

async def broadcast_system_message(text: str) -> None:
    """Publica un mensaje de sistema en el chat y lo persiste en BD."""
    async with AsyncSessionLocal() as db:
        msg = await _persist(
            db,
            sender_name="Sistema",
            sender_role="system",
            text=text,
            is_system=True,
            created_at=datetime.utcnow(),
        )
    await manager.broadcast({"type": "message", "data": _msg_payload(msg)})


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def chat_ws(
    ws: WebSocket,
    token: str = Query(...),
):
    # Validar JWT
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: int = int(payload.get("sub"))
    except (JWTError, Exception):
        await ws.close(code=1008)
        return

    async with AsyncSessionLocal() as db:
        user: Optional[User] = (
            await db.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    if not user or not user.is_active:
        await ws.close(code=1008)
        return

    allowed = ("volunteer", "coordinator", "admin")
    user_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if user_role not in allowed:
        await ws.close(code=1008)
        return

    name = f"{user.full_name}" + (f" {user.last_name}" if user.last_name else "")
    role = user.role.value if hasattr(user.role, "value") else str(user.role)

    await manager.connect(ws, user_id, name, role)
    online = await manager.online_count()

    # Enviar historial
    async with AsyncSessionLocal() as db:
        history = await _get_history(db)
    await ws.send_json({"type": "history", "data": history, "online": online})

    # Notificar entrada (efímero, no persiste en BD)
    join_payload = {
        "id": None, "user_id": user_id, "sender_name": "Sistema", "sender_role": "system",
        "text": f"{name} se conectó.", "is_system": True,
        "created_at": datetime.utcnow().isoformat() + "Z", "ephemeral": True,
    }
    await manager.broadcast({"type": "message", "data": join_payload, "online": await manager.online_count()})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
                text = str(data.get("text", "")).strip()[:500]
            except Exception:
                text = raw.strip()[:500]

            if not text:
                continue

            async with AsyncSessionLocal() as db:
                msg = await _persist(
                    db,
                    channel="group",
                    user_id=user_id,
                    sender_name=name,
                    sender_role=role,
                    text=text,
                    is_system=False,
                    created_at=datetime.utcnow(),
                )
            await manager.broadcast({
                "type": "message",
                "data": _msg_payload(msg),
                "online": await manager.online_count(),
            })

    except WebSocketDisconnect:
        info = await manager.disconnect(ws)
        if info:
            leave_payload = {
                "id": None, "user_id": None, "sender_name": "Sistema", "sender_role": "system",
                "text": f"{info['name']} se desconectó.", "is_system": True,
                "created_at": datetime.utcnow().isoformat() + "Z", "ephemeral": True,
            }
            await manager.broadcast({
                "type": "message",
                "data": leave_payload,
                "online": await manager.online_count(),
            })
    except Exception as exc:
        log.error("Chat WS error: %s", exc)
        await manager.disconnect(ws)
