"""
Servicio de envío de SMS via Inalambria Internacional.
Docs: https://docs.inalambria.com/reference/new-endpoint.md
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

INALAMBRIA_BASE = "https://rest.inalambria.com"

# Cache simple en memoria del token (evita pedir uno nuevo en cada SMS)
_token_cache: dict = {"access_token": None, "expires_at": 0}
_token_lock = asyncio.Lock()


def _normalize_phone(phone: str) -> Optional[str]:
    """
    Normaliza un número colombiano a formato 57XXXXXXXXXX (12 dígitos).
    Acepta: 3XXXXXXXXX, 03XXXXXXXXX, +573XXXXXXXXX, 573XXXXXXXXX, con espacios/guiones.
    Retorna None si no es válido.
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("57") and len(digits) == 12:
        return digits
    if digits.startswith("0") and len(digits) == 11:
        return "57" + digits[1:]
    if len(digits) == 10 and digits.startswith("3"):
        return "57" + digits
    logger.warning("Número de teléfono inválido, se omite: %s", phone)
    return None


async def _get_token() -> Optional[str]:
    """Obtiene (o reutiliza) el Bearer token de Inalambria."""
    if not settings.INALAMBRIA_USER or not settings.INALAMBRIA_PASS:
        logger.warning("Credenciales Inalambria no configuradas — SMS desactivado")
        return None

    async with _token_lock:
        now = time.time()
        # Reutilizar si aún tiene > 5 minutos de vida
        if _token_cache["access_token"] and now < _token_cache["expires_at"] - 300:
            return _token_cache["access_token"]

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{INALAMBRIA_BASE}/token",
                    json={"grant_type": "password"},
                    auth=(settings.INALAMBRIA_USER, settings.INALAMBRIA_PASS),
                )
                resp.raise_for_status()
                data = resp.json()
                _token_cache["access_token"] = data["access_token"]
                _token_cache["expires_at"] = now + int(data.get("expires_in", 14400))
                logger.info("Token Inalambria obtenido — expira en %ds", data.get("expires_in", 14400))
                return _token_cache["access_token"]
        except Exception as exc:
            logger.error("Error obteniendo token Inalambria: %s", exc)
            return None


async def send_sms(phones: list[str], message: str) -> bool:
    """
    Envía un SMS a uno o varios números colombianos.

    Args:
        phones: lista de números (cualquier formato colombiano)
        message: texto del mensaje (máx. 500 caracteres recomendado)

    Returns:
        True si el envío fue aceptado por Inalambria, False en caso contrario.
    """
    if not phones:
        return False

    # Normalizar y filtrar números inválidos
    normalized = [_normalize_phone(p) for p in phones]
    valid = [p for p in normalized if p]

    if not valid:
        logger.warning("send_sms: ningún número válido en %s", phones)
        return False

    token = await _get_token()
    if not token:
        return False

    # Inalambria acepta múltiples números separados por guión
    devices = "-".join(valid)
    payload = {
        "Type": 1,
        "Devices": devices,
        "MessageText": message[:500],
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{INALAMBRIA_BASE}/mtmessage",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            result = resp.json()
            if result.get("Status") == 0:
                logger.info("SMS enviado a %d número(s). Transacción: %s", len(valid), result.get("TransactionNumber"))
                return True
            else:
                logger.error("Inalambria rechazó el SMS: %s", result.get("MessageText"))
                return False
    except Exception as exc:
        logger.error("Error enviando SMS via Inalambria: %s", exc)
        return False


# ─── Mensajes predefinidos ───────────────────────────────────────────────────

def msg_nuevo_reporte(need_type: str, address: str, report_id: int) -> str:
    tipos = {
        "food": "🍲 Alimentos",
        "water": "💧 Agua",
        "medical": "🏥 Ayuda médica",
        "shelter": "🏠 Refugio",
        "rescue": "🆘 Rescate",
        "psychological": "🧠 Apoyo psicológico",
        "clothing": "👕 Ropa",
        "pet": "🐾 Mascota perdida",
        "pet_home": "🐾 Mascota busca hogar",
        "other": "📋 Otra necesidad",
    }
    tipo_label = tipos.get(need_type, need_type)
    return (
        f"[Te Ayudo Pereira] Nueva solicitud #{report_id}: {tipo_label} "
        f"en {address}. Ingresa a teayudopereira.com para atender."
    )


def msg_asignado(volunteer_name: str, report_id: int, contact_name: str, contact_phone: str) -> str:
    return (
        f"[Te Ayudo Pereira] Hola {volunteer_name}, se te asignó el caso #{report_id}. "
        f"Contacta a {contact_name} al {contact_phone}. teayudopereira.com"
    )


def msg_zona_peligro(danger_name: str, danger_level: str, address: str) -> str:
    niveles = {"low": "⚠️ Precaución", "medium": "🟠 Peligro moderado", "high": "🔴 Peligro alto", "critical": "🚨 EVACUACIÓN"}
    nivel_label = niveles.get(danger_level, danger_level)
    return (
        f"[Te Ayudo Pereira] ALERTA {nivel_label}: {danger_name} reportado en {address}. "
        f"Evita la zona. Info: teayudopereira.com"
    )
