"""
broadcaster.py — Pub/Sub multi-worker vía Redis.

Cada worker mantiene sus propias conexiones WebSocket en memoria.
Cuando un mensaje debe enviarse a todos los usuarios, se publica en Redis.
Todos los workers escuchan Redis y reenvían a sus conexiones locales.

Esto garantiza que dos usuarios conectados a workers distintos
puedan comunicarse sin problemas.

Uso:
    from app.services.broadcaster import group_broadcaster, room_broadcaster

    # En lifespan (main.py):
    await group_broadcaster.setup(settings.REDIS_URL)
    await room_broadcaster.setup(settings.REDIS_URL)
    yield
    await group_broadcaster.teardown()
    await room_broadcaster.teardown()
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Optional

from fastapi import WebSocket

log = logging.getLogger(__name__)

# ─── Chat grupal ──────────────────────────────────────────────────────────────

class GroupBroadcaster:
    """
    Broadcaster para el canal de chat grupal.

    - Publica mensajes en Redis → todos los workers los reciben.
    - Rastrea usuarios online con un Redis SET para conteo global.
    """

    CHANNEL = "teayudo:chat:group"
    ONLINE_KEY = "teayudo:chat:online"

    def __init__(self) -> None:
        self._connections: Dict[WebSocket, dict] = {}
        self._redis = None
        self._redis_url: str = "redis://localhost:6379/0"
        self._listener_task: Optional[asyncio.Task] = None

    async def setup(self, redis_url: str) -> None:
        import redis.asyncio as aioredis
        self._redis_url = redis_url
        self._redis = await aioredis.from_url(redis_url, decode_responses=True)
        self._listener_task = asyncio.create_task(self._listen())
        log.info("GroupBroadcaster: Redis conectado — canal %s", self.CHANNEL)

    async def teardown(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
        log.info("GroupBroadcaster: cerrado")

    # ── Gestión de conexiones ──────────────────────────────────────────────

    async def connect(self, ws: WebSocket, user_id: int, name: str, role: str) -> None:
        await ws.accept()
        self._connections[ws] = {"user_id": user_id, "name": name, "role": role}
        await self._redis.sadd(self.ONLINE_KEY, user_id)
        log.info("Chat connect: %s (%s)", name, role)

    async def disconnect(self, ws: WebSocket) -> Optional[dict]:
        info = self._connections.pop(ws, None)
        if info:
            await self._redis.srem(self.ONLINE_KEY, info["user_id"])
            log.info("Chat disconnect: %s", info["name"])
        return info

    async def online_count(self) -> int:
        return await self._redis.scard(self.ONLINE_KEY)

    # ── Broadcast ─────────────────────────────────────────────────────────

    async def broadcast(self, payload: dict) -> None:
        """Publica en Redis; todos los workers lo recibirán y enviarán localmente."""
        await self._redis.publish(self.CHANNEL, json.dumps(payload))

    # ── Listener interno (tarea de fondo por worker) ───────────────────────

    async def _listen(self) -> None:
        import redis.asyncio as aioredis
        # Conexión dedicada para pubsub (no puede compartirse con comandos normales)
        r = await aioredis.from_url(self._redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(self.CHANNEL)
        log.info("GroupBroadcaster: escuchando canal %s", self.CHANNEL)
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    payload = json.loads(message["data"])
                except Exception:
                    continue
                await self._send_local(payload)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(self.CHANNEL)
        except Exception as exc:
            log.error("GroupBroadcaster listener error: %s", exc)
        finally:
            await r.aclose()

    async def _send_local(self, payload: dict) -> None:
        dead: List[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._connections.pop(ws, None)


# ─── DMs / Salas ─────────────────────────────────────────────────────────────

class RoomBroadcaster:
    """
    Broadcaster para mensajes directos y salas de guest.

    - Una sala = un canal Redis "teayudo:chat:room:<room>"
    - Usa psubscribe para escuchar todas las salas con un solo listener.
    """

    CHANNEL_PREFIX = "teayudo:chat:room:"

    def __init__(self) -> None:
        self._rooms: Dict[str, Dict[WebSocket, dict]] = {}
        self._redis = None
        self._redis_url: str = "redis://localhost:6379/0"
        self._listener_task: Optional[asyncio.Task] = None

    async def setup(self, redis_url: str) -> None:
        import redis.asyncio as aioredis
        self._redis_url = redis_url
        self._redis = await aioredis.from_url(redis_url, decode_responses=True)
        self._listener_task = asyncio.create_task(self._listen())
        log.info("RoomBroadcaster: Redis conectado — patrón %s*", self.CHANNEL_PREFIX)

    async def teardown(self) -> None:
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
        if self._redis:
            await self._redis.aclose()
        log.info("RoomBroadcaster: cerrado")

    # ── Gestión de conexiones ──────────────────────────────────────────────

    def _room(self, room: str) -> Dict[WebSocket, dict]:
        return self._rooms.setdefault(room, {})

    def get_local_room(self, room: str) -> Dict[WebSocket, dict]:
        """Retorna las conexiones locales de una sala (compatible con código previo)."""
        return self._rooms.get(room, {})

    async def connect(
        self, ws: WebSocket, room: str, user_id: int, name: str, role: str
    ) -> None:
        await ws.accept()
        self._room(room)[ws] = {"user_id": user_id, "name": name, "role": role}

    def disconnect(self, ws: WebSocket, room: str) -> None:
        self._room(room).pop(ws, None)
        if not self._room(room):
            self._rooms.pop(room, None)

    # ── Broadcast ─────────────────────────────────────────────────────────

    async def broadcast(self, room: str, payload: dict) -> None:
        channel = f"{self.CHANNEL_PREFIX}{room}"
        await self._redis.publish(channel, json.dumps(payload))

    # ── Listener interno ──────────────────────────────────────────────────

    async def _listen(self) -> None:
        import redis.asyncio as aioredis
        r = await aioredis.from_url(self._redis_url, decode_responses=True)
        pubsub = r.pubsub()
        pattern = f"{self.CHANNEL_PREFIX}*"
        await pubsub.psubscribe(pattern)
        log.info("RoomBroadcaster: escuchando patrón %s", pattern)
        try:
            async for message in pubsub.listen():
                if message["type"] != "pmessage":
                    continue
                try:
                    channel: str = message["channel"]
                    room = channel.removeprefix(self.CHANNEL_PREFIX)
                    payload = json.loads(message["data"])
                except Exception:
                    continue
                await self._send_local(room, payload)
        except asyncio.CancelledError:
            await pubsub.punsubscribe(pattern)
        except Exception as exc:
            log.error("RoomBroadcaster listener error: %s", exc)
        finally:
            await r.aclose()

    async def _send_local(self, room: str, payload: dict) -> None:
        dead: List[WebSocket] = []
        for ws in list(self._room(room)):
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._room(room).pop(ws, None)


# ─── Singletons (uno por worker, coordinados vía Redis) ───────────────────────

group_broadcaster = GroupBroadcaster()
room_broadcaster = RoomBroadcaster()
