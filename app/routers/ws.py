from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws/trace")
async def trace_websocket(ws: WebSocket):
    """
    Persistent WebSocket connection for the MVC Simulator.

    The simulator connects here on load and stays connected.
    Whenever a real API request completes (upload, chat, task, register),
    FastAPI pushes the recorded trace to all connected simulators.

    No polling, no manual button – fully automatic.
    """
    await manager.connect(ws)
    try:
        while True:
            # Keep connection alive – simulator can send "ping" if needed
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        manager.disconnect(ws)