"""
Web Push — notificaciones push para usuarios autenticados y guests.

Endpoints:
  GET  /push/vapid-public-key  → devuelve la clave pública VAPID (sin auth)
  POST /push/subscribe         → guarda suscripción (auth JWT o guest_token)
  POST /push/unsubscribe       → elimina suscripción del endpoint
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.push_subscription import PushSubscription
from app.models.user import User
from app.services.auth import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(tags=["Push"])


# ─── Clave pública ────────────────────────────────────────────────────────────

@router.get("/push/vapid-public-key")
async def vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}


# ─── Suscripción ─────────────────────────────────────────────────────────────

@router.post("/push/subscribe")
async def subscribe(
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    body: {
      subscription: { endpoint, keys: { p256dh, auth } },
      guest_token?: str   # para ciudadanos anónimos
    }
    Header Authorization: Bearer <token>  ← opcional (si no viene, se usa guest_token)
    """
    sub = body.get("subscription", {})
    endpoint = sub.get("endpoint", "")
    p256dh   = (sub.get("keys") or {}).get("p256dh", "")
    auth     = (sub.get("keys") or {}).get("auth", "")
    guest_token: Optional[str] = body.get("guest_token")

    if not endpoint or not p256dh or not auth:
        raise HTTPException(400, "Suscripción incompleta")

    # Intentar obtener usuario del header si viene (no requerimos auth)
    user_id: Optional[int] = None
    auth_header = body.get("_auth_header")  # pasado desde el cliente

    # Evitar duplicados por endpoint
    existing = (await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )).scalar_one_or_none()

    if existing:
        # Actualizar
        existing.p256dh = p256dh
        existing.auth = auth
        if guest_token:
            existing.guest_token = guest_token
        await db.commit()
        return {"status": "updated"}

    ps = PushSubscription(
        user_id=user_id,
        guest_token=guest_token,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth,
    )
    db.add(ps)
    await db.commit()
    return {"status": "subscribed"}


@router.post("/push/subscribe/auth")
async def subscribe_auth(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Igual que subscribe pero con JWT — guarda user_id."""
    sub = body.get("subscription", {})
    endpoint = sub.get("endpoint", "")
    p256dh   = (sub.get("keys") or {}).get("p256dh", "")
    auth_key = (sub.get("keys") or {}).get("auth", "")

    if not endpoint or not p256dh or not auth_key:
        raise HTTPException(400, "Suscripción incompleta")

    existing = (await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )).scalar_one_or_none()

    if existing:
        existing.p256dh = p256dh
        existing.auth = auth_key
        existing.user_id = current_user.id
        existing.guest_token = None
        await db.commit()
        return {"status": "updated"}

    ps = PushSubscription(
        user_id=current_user.id,
        guest_token=None,
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth_key,
    )
    db.add(ps)
    await db.commit()
    return {"status": "subscribed"}


@router.delete("/push/unsubscribe")
async def unsubscribe(body: dict, db: AsyncSession = Depends(get_db)):
    endpoint = body.get("endpoint", "")
    if endpoint:
        await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))
        await db.commit()
    return {"status": "unsubscribed"}


# ─── Helper de envío (usado por otros routers) ────────────────────────────────

async def send_push_to_user(
    db: AsyncSession,
    user_id: int,
    title: str,
    body: str,
    url: str = "/",
) -> None:
    """Envía push a todas las suscripciones de un usuario autenticado."""
    subs = (await db.execute(
        select(PushSubscription).where(PushSubscription.user_id == user_id)
    )).scalars().all()
    await _send_to_subs(subs, title, body, url)


async def send_push_to_guest(
    db: AsyncSession,
    guest_token: str,
    title: str,
    body: str,
    url: str = "/",
) -> None:
    """Envía push a todas las suscripciones de un ciudadano anónimo."""
    subs = (await db.execute(
        select(PushSubscription).where(PushSubscription.guest_token == guest_token)
    )).scalars().all()
    await _send_to_subs(subs, title, body, url)


async def send_push_to_admins(
    db: AsyncSession,
    title: str,
    body: str,
    url: str = "/",
) -> None:
    """Envía push a todos los admins/coordinadores."""
    from app.models.user import User, UserRole
    from sqlalchemy import select as sel
    admins = (await db.execute(
        sel(User).where(
            User.role.in_([UserRole.admin, UserRole.coordinator]),
            User.is_active == True,  # noqa
        )
    )).scalars().all()
    admin_ids = [a.id for a in admins]
    if not admin_ids:
        return
    subs = (await db.execute(
        select(PushSubscription).where(PushSubscription.user_id.in_(admin_ids))
    )).scalars().all()
    await _send_to_subs(subs, title, body, url)


async def _send_to_subs(subs, title: str, body: str, url: str) -> None:
    if not subs:
        return
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log.warning("pywebpush no instalado — push deshabilitado")
        return

    payload = json.dumps({"title": title, "body": body, "url": url})
    vapid_claims = {"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"}

    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
        except WebPushException as e:
            status = e.response.status_code if e.response else 0
            if status in (404, 410):
                # Suscripción expirada — se limpia en background (no bloqueamos)
                log.info("Push subscription expirada: %s", sub.endpoint[:60])
            else:
                log.warning("Push error (%s): %s", status, str(e)[:120])
        except Exception as e:
            log.warning("Push send error: %s", str(e)[:120])
