from fastapi import WebSocket
from typing import List
import json


class TraceConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast_trace(self, trace: list, endpoint: str,
                              extras: dict = None):
        """
        Push trace + optional extras (e.g. chunk_stats) to all simulators.
        """
        payload = {
            "type":     "live_trace",
            "endpoint": endpoint,
            "steps":    trace,
        }
        if extras:
            payload.update(extras)   # adds chunk_stats to payload

        data = json.dumps(payload)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = TraceConnectionManager()