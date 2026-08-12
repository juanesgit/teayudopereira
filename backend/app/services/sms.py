"""
Servicio SMS via Inalambria Express API v1.
Docs: https://github.com/InalambriaExpress/inalambria-express-api-docs
Base URL: https://api.inalambria.express/v1
Auth: Bearer token (API key sk_live_...)
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INALAMBRIA_BASE = "https://api.inalambria.express/v1"


def _normalize_phone(phone: str) -> Optional[str]:
    """
    Normaliza número colombiano a formato E.164 (+57XXXXXXXXXX).
    Acepta: 3XXXXXXXXX, 573XXXXXXXXX, +573XXXXXXXXX, con espacios/guiones.
    """
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 10 and digits.startswith("3"):
        return f"+57{digits}"
    if digits.startswith("57") and len(digits) == 12:
        return f"+{digits}"
    if digits.startswith("573") and len(digits) == 12:
        return f"+{digits}"
    logger.warning("Número inválido, se omite: %s", phone)
    return None


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.INALAMBRIA_API_KEY}",
        "Content-Type": "application/json",
    }


async def send_sms(phones: list[str], message: str) -> bool:
    """
    Envía el mismo SMS a uno o varios números.
    Usa POST /messages/send con async=False para confirmar entrega.
    Returns True si fue aceptado.
    """
    if not settings.INALAMBRIA_API_KEY:
        logger.warning("INALAMBRIA_API_KEY no configurado — SMS desactivado")
        return False

    valid = [n for n in (_normalize_phone(p) for p in phones) if n]
    if not valid:
        logger.warning("send_sms: ningún número válido en %s", phones)
        return False

    payload = {
        "content": message[:500],
        "recipients": valid,
        "async": True,   # retorna jobId inmediatamente, no bloquea
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{INALAMBRIA_BASE}/messages/send",
                json=payload,
                headers=_headers(),
            )
            data = resp.json()

            if resp.status_code in (200, 202):
                job_id = data.get("jobId", "")
                consumption_id = data.get("consumptionId", "")
                logger.info(
                    "SMS enviado a %d número(s). jobId=%s consumptionId=%s",
                    len(valid), job_id, consumption_id,
                )
                return True
            else:
                logger.error(
                    "Inalambria rechazó SMS [%d]: %s",
                    resp.status_code,
                    data.get("error", resp.text),
                )
                return False
    except Exception as exc:
        logger.error("Error enviando SMS via Inalambria Express: %s", exc)
        return False


async def get_balance() -> Optional[dict]:
    """Consulta el saldo de créditos disponibles."""
    if not settings.INALAMBRIA_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{INALAMBRIA_BASE}/messages/balance",
                headers=_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.error("Error consultando saldo Inalambria: %s", exc)
    return None


async def get_history(limit: int = 20, offset: int = 0) -> Optional[dict]:
    """Consulta el historial de mensajes enviados."""
    if not settings.INALAMBRIA_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{INALAMBRIA_BASE}/messages/history",
                params={"limit": limit, "offset": offset},
                headers=_headers(),
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as exc:
        logger.error("Error consultando historial Inalambria: %s", exc)
    return None


# ─── Plantillas de mensajes ───────────────────────────────────────────────────

def msg_nuevo_reporte(need_type: str, address: str, report_id: int) -> str:
    tipos = {
        "food": "Alimentos", "water": "Agua", "medical": "Ayuda médica",
        "shelter": "Refugio", "rescue": "Rescate", "psychological": "Apoyo psicológico",
        "clothing": "Ropa", "pet": "Mascota perdida", "pet_home": "Mascota busca hogar",
        "other": "Otra necesidad",
    }
    return (
        f"[TeAyudoPereira] Nueva solicitud #{report_id}: "
        f"{tipos.get(need_type, need_type)} en {address}. "
        f"Atiende en teayudopereira.com"
    )


def msg_asignado(volunteer_name: str, report_id: int, contact_name: str, contact_phone: str) -> str:
    return (
        f"[TeAyudoPereira] Hola {volunteer_name}, tienes el caso #{report_id}. "
        f"Contacta a {contact_name} al {contact_phone}. teayudopereira.com"
    )


def msg_zona_peligro(danger_name: str, danger_level: str, address: str) -> str:
    niveles = {
        "low": "Precaucion", "medium": "Peligro moderado",
        "high": "PELIGRO ALTO", "critical": "EVACUACION INMEDIATA",
    }
    return (
        f"[TeAyudoPereira] ALERTA {niveles.get(danger_level, danger_level)}: "
        f"{danger_name} en {address}. Evita la zona. teayudopereira.com"
    )
