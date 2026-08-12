"""
Servicio de envío de SMS via Inalambria Internacional.
Docs: https://docs.inalambria.com/reference/new-endpoint.md

Autenticación: API Key usada directamente como Bearer token.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INALAMBRIA_BASE = "https://rest.inalambria.com"


def _normalize_phone(phone: str) -> Optional[str]:
    """
    Normaliza número colombiano a 57XXXXXXXXXX (12 dígitos).
    Acepta: 3XXXXXXXXX, +573XXXXXXXXX, 573XXXXXXXXX, con espacios/guiones.
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("57") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "57" + digits[1:]
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    logger.warning("Número inválido, se omite: %s", phone)
    return None


async def send_sms(phones: list[str], message: str) -> bool:
    """
    Envía SMS a uno o varios números colombianos.
    Returns True si Inalambria lo aceptó.
    """
    if not settings.INALAMBRIA_API_KEY:
        logger.warning("INALAMBRIA_API_KEY no configurado — SMS desactivado")
        return False

    if not phones:
        return False

    valid = [n for n in (_normalize_phone(p) for p in phones) if n]
    if not valid:
        logger.warning("send_sms: ningún número válido en %s", phones)
        return False

    payload = {
        "Type": 1,
        "Devices": "-".join(valid),
        "MessageText": message[:500],
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{INALAMBRIA_BASE}/mtmessage",
                json=payload,
                headers={"Authorization": f"Bearer {settings.INALAMBRIA_API_KEY}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("Status") == 0:
                logger.info(
                    "SMS enviado a %d número(s). Transacción: %s",
                    len(valid),
                    result.get("TransactionNumber"),
                )
                return True
            else:
                logger.error("Inalambria rechazó el SMS: %s", result.get("MessageText"))
                return False
    except Exception as exc:
        logger.error("Error enviando SMS via Inalambria: %s", exc)
        return False


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
