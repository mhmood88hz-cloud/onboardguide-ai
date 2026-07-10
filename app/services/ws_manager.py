from fastapi import WebSocket
from typing import List
import json


class TraceConnectionManager:
    """
    Manages all active WebSocket connections to the simulator.
    When a real API request completes, the trace is broadcast
    to every connected simulator instance in real time.
    """

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast_trace(self, trace: list, endpoint: str):
        """
        Push the recorded trace to every connected simulator.
        Payload format matches exactly what the simulator JS expects.
        """
        payload = json.dumps({
            "type":     "live_trace",
            "endpoint": endpoint,
            "steps":    trace
        })
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


# Singleton – imported by routers and services
manager = TraceConnectionManager()