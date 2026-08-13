"""
Chat anónimo para ciudadanos/víctimas sin login.

Flujo:
  1. POST /dm/guest-session  { name, report_id? }
     → crea GuestSession, devuelve { guest_token, room, guest_name }
  2. GET  /dm/guest-session/{guest_token}
     → restaura sesión desde localStorage al recargar
  3. WS   /ws/guest/{room}?guest_token={token}
     → el ciudadano envía/recibe mensajes
  4. El admin se conecta a la misma sala vía /ws/dm/{room} (JWT normal)
     dm.py ya permite admin en salas guest_*
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.chat import ChatMessage
from app.models.guest_session import GuestSession
from app.routers.dm import dm_manager, _msg_payload, _persist, _get_history

log = logging.getLogger(__name__)
router = APIRouter(tags=["GuestChat"])


# ─── REST ────────────────────────────────────────────────────────────────────

@router.post("/dm/guest-session")
async def create_guest_session(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """Crea o recupera una sesión anónima. Idempotente si ya existe token."""
    name = str(body.get("name", "")).strip()[:80]
    if not name:
        raise HTTPException(400, "Se requiere un nombre")

    report_id: Optional[int] = body.get("report_id")

    token = secrets.token_hex(32)           # 64 chars hex
    room  = f"guest_{secrets.token_hex(16)}"  # único por sesión

    gs = GuestSession(
        guest_token=token,
        guest_name=name,
        room=room,
        report_id=report_id,
        created_at=datetime.utcnow(),
    )
    db.add(gs)
    await db.commit()
    await db.refresh(gs)

    return {"guest_token": token, "room": room, "guest_name": name}


@router.get("/dm/guest-session/{guest_token}")
async def get_guest_session(
    guest_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Restaura la sesión guardada en localStorage."""
    gs = (await db.execute(
        select(GuestSession).where(GuestSession.guest_token == guest_token)
    )).scalar_one_or_none()

    if not gs:
        raise HTTPException(404, "Sesión no encontrada")

    return {
        "guest_token": gs.guest_token,
        "room": gs.room,
        "guest_name": gs.guest_name,
        "report_id": gs.report_id,
    }


# ─── WebSocket anónimo ────────────────────────────────────────────────────────

@router.websocket("/ws/guest/{room}")
async def guest_ws(
    ws: WebSocket,
    room: str,
    guest_token: str = Query(...),
):
    # Validar token
    async with AsyncSessionLocal() as db:
        gs: Optional[GuestSession] = (await db.execute(
            select(GuestSession).where(
                GuestSession.guest_token == guest_token,
                GuestSession.room == room,
            )
        )).scalar_one_or_none()

    if not gs:
        await ws.close(code=1008)
        return

    name = gs.guest_name
    role = "victim"

    await dm_manager.connect(ws, room, 0, name, role)  # user_id=0 para guests

    # Historial
    async with AsyncSessionLocal() as db:
        history = await _get_history(db, room)

    await ws.send_json({"type": "history", "data": history})

    # Mensaje de contexto si viene de un reporte (solo si no hay historial)
    if gs.report_id and not history:
        ctx_text = f"[Reporte #{gs.report_id}] {name} inició una conversación desde su solicitud de ayuda."
        async with AsyncSessionLocal() as db:
            ctx_msg = await _persist(
                db, channel=room,
                user_id=None, sender_name="Sistema", sender_role="system",
                text=ctx_text, is_system=True, is_read=False,
                created_at=datetime.utcnow(),
            )
        await dm_manager.broadcast(room, {"type": "message", "data": _msg_payload(ctx_msg)})

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
                    user_id=None, sender_name=name, sender_role=role,
                    text=text, is_system=False, is_read=False,
                    created_at=datetime.utcnow(),
                )
            await dm_manager.broadcast(room, {"type": "message", "data": _msg_payload(msg)})

    except WebSocketDisconnect:
        dm_manager.disconnect(ws, room)
    except Exception as exc:
        log.error("Guest WS error: %s", exc)
        dm_manager.disconnect(ws, room)
