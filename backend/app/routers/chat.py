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
from typing import Dict, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jose import JWTError, jwt

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.chat import ChatMessage
from app.models.user import User

log = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])

# ─── Connection manager ───────────────────────────────────────────────────────

class ConnectionManager:
    def __init__(self) -> None:
        # websocket → {"user_id": int, "name": str, "role": str}
        self._connections: Dict[WebSocket, dict] = {}

    def online_count(self) -> int:
        return len(self._connections)

    async def connect(self, ws: WebSocket, user_id: int, name: str, role: str) -> None:
        await ws.accept()
        self._connections[ws] = {"user_id": user_id, "name": name, "role": role}
        log.info("Chat connect: %s (%s) — %d online", name, role, self.online_count())

    def disconnect(self, ws: WebSocket) -> Optional[dict]:
        info = self._connections.pop(ws, None)
        if info:
            log.info("Chat disconnect: %s — %d online", info["name"], self.online_count())
        return info

    async def broadcast(self, payload: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.pop(ws, None)


manager = ConnectionManager()

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
        "created_at": msg.created_at.isoformat(),
    }


async def _get_history(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(ChatMessage)
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
        user: Optional[User] = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

    if not user or not user.is_active:
        await ws.close(code=1008)
        return

    name = f"{user.full_name}" + (f" {user.last_name}" if user.last_name else "")
    role = user.role.value if hasattr(user.role, "value") else str(user.role)

    await manager.connect(ws, user_id, name, role)

    # Enviar historial
    async with AsyncSessionLocal() as db:
        history = await _get_history(db)
    await ws.send_json({"type": "history", "data": history, "online": manager.online_count()})

    # Notificar efímeramente que alguien entró (no se persiste en BD)
    join_payload = {
        "id": None, "user_id": user_id, "sender_name": "Sistema", "sender_role": "system",
        "text": f"{name} se conectó.", "is_system": True,
        "created_at": datetime.utcnow().isoformat(), "ephemeral": True,
    }
    await manager.broadcast({"type": "message", "data": join_payload, "online": manager.online_count()})

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
                    user_id=user_id,
                    sender_name=name,
                    sender_role=role,
                    text=text,
                    is_system=False,
                    created_at=datetime.utcnow(),
                )
            await manager.broadcast({"type": "message", "data": _msg_payload(msg), "online": manager.online_count()})

    except WebSocketDisconnect:
        info = manager.disconnect(ws)
        if info:
            leave_payload = {
                "id": None, "user_id": None, "sender_name": "Sistema", "sender_role": "system",
                "text": f"{info['name']} se desconectó.", "is_system": True,
                "created_at": datetime.utcnow().isoformat(), "ephemeral": True,
            }
            await manager.broadcast({"type": "message", "data": leave_payload, "online": manager.online_count()})
    except Exception as exc:
        log.error("Chat WS error: %s", exc)
        manager.disconnect(ws)
