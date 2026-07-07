from __future__ import annotations

from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, Dict[str, WebSocket]] = {}

    async def connect(self, masjid_id: str, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        if masjid_id not in self._connections:
            self._connections[masjid_id] = {}
        self._connections[masjid_id][user_id] = ws

    async def disconnect(self, masjid_id: str, user_id: str) -> None:
        if masjid_id in self._connections:
            self._connections[masjid_id].pop(user_id, None)
            if not self._connections[masjid_id]:
                del self._connections[masjid_id]

    async def broadcast_to_masjid(self, masjid_id: str, message: dict) -> None:
        if masjid_id not in self._connections:
            return
        disconnected = []
        for uid, ws in self._connections[masjid_id].items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(uid)
        for uid in disconnected:
            await self.disconnect(masjid_id, uid)

    async def send_to_user(self, masjid_id: str, user_id: str, message: dict) -> None:
        if masjid_id not in self._connections:
            return
        ws = self._connections[masjid_id].get(user_id)
        if ws is None:
            return
        try:
            await ws.send_json(message)
        except Exception:
            await self.disconnect(masjid_id, user_id)

    def get_connected_users(self, masjid_id: str) -> List[str]:
        return list(self._connections.get(masjid_id, {}).keys())