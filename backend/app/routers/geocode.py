"""
Proxy para Nominatim (OpenStreetMap geocoding).

Ventajas vs. llamada directa desde el browser:
  - Sin problemas de CORS
  - Rate-limit controlado desde el servidor (una sola IP)
  - Cache en memoria para evitar peticiones duplicadas
"""

from __future__ import annotations

import time
import httpx
from fastapi import APIRouter, Query, HTTPException
from typing import Optional

router = APIRouter(prefix="/geocode", tags=["Geocoding"])

# ── Cache simple en memoria (TTL 10 min) ─────────────────────────────────────
_cache: dict[str, tuple[float, list]] = {}
_CACHE_TTL = 600  # segundos

NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
HEADERS = {
    "User-Agent": "TeAyudoPereira/1.0 (teayudopereira.com)",
    "Accept-Language": "es",
}


def _cache_get(key: str) -> list | None:
    entry = _cache.get(key)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        return entry[1]
    return None


def _cache_set(key: str, value: list) -> None:
    # Limpiar entradas viejas si el cache crece mucho
    if len(_cache) > 500:
        cutoff = time.time() - _CACHE_TTL
        for k in list(_cache.keys()):
            if _cache[k][0] < cutoff:
                del _cache[k]
    _cache[key] = (time.time(), value)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/search")
async def geocode_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(6, ge=1, le=10),
):
    """
    Búsqueda de dirección → lista de resultados.
    Hace hasta 3 queries a Nominatim (viewbox + Pereira + Dosquebradas)
    pero las cachea para no repetir la misma búsqueda.
    """
    q = q.strip()
    cache_key = f"search:{q.lower()}:{limit}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    base = f"{NOMINATIM_BASE}/search?format=json&limit=4&accept-language=es&countrycodes=co"
    vbox = "&viewbox=-75.80,4.57,-75.45,4.95&bounded=1"
    import urllib.parse
    s = urllib.parse.quote(q)
    s_pereira = urllib.parse.quote(f"{q}, Pereira, Risaralda")
    s_dosq = urllib.parse.quote(f"{q}, Dosquebradas, Risaralda")

    urls = [
        f"{base}{vbox}&q={s}",
        f"{base}&q={s_pereira}",
        f"{base}&q={s_dosq}",
    ]

    results: list = []
    seen: set = set()

    async with httpx.AsyncClient(timeout=8.0) as client:
        for url in urls:
            try:
                r = await client.get(url, headers=HEADERS)
                if r.status_code == 200:
                    for item in r.json():
                        pid = item.get("place_id")
                        if pid and pid not in seen:
                            seen.add(pid)
                            results.append(item)
            except Exception:
                continue
            # Respetar rate-limit de Nominatim: 1 req/s
            import asyncio
            await asyncio.sleep(1.1)

    final = results[:limit]
    _cache_set(cache_key, final)
    return final


@router.get("/reverse")
async def geocode_reverse(
    lat: float = Query(...),
    lng: float = Query(...),
):
    """Geocodificación inversa: coordenadas → dirección."""
    cache_key = f"reverse:{lat:.5f}:{lng:.5f}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    url = f"{NOMINATIM_BASE}/reverse?format=json&lat={lat}&lon={lng}&accept-language=es"

    async with httpx.AsyncClient(timeout=8.0) as client:
        try:
            r = await client.get(url, headers=HEADERS)
            if r.status_code != 200:
                raise HTTPException(502, "Error en geocodificación inversa")
            data = r.json()
        except httpx.RequestError:
            raise HTTPException(502, "No se pudo contactar el servicio de geocodificación")

    _cache_set(cache_key, data)
    return data
