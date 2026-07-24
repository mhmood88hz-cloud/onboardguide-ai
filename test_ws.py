import asyncio
import websockets

async def test():
    try:
        async with websockets.connect("ws://localhost:8000/ws/trace") as ws:
            print("Verbunden!")
            await ws.send("ping")
            msg = await asyncio.wait_for(ws.recv(), timeout=3)
            print("Antwort:", msg)
    except Exception as e:
        print("Fehler:", e)

asyncio.run(test())
