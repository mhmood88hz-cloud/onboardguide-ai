from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import Base, engine, get_db
from app.routers import auth, users, tasks, documents, chat, ws

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OnboardGuide AI Backend",
    description="MVC modular design with Live Trace Simulator.",
    version="1.4.0"
)

# CORS – needed for Swagger UI + expose trace header
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Workflow-Trace"],
)

# Register all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(ws.router)        # WebSocket /ws/trace


@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    """Health check."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status":    "online",
            "database":  "onboardguide_db",
            "version":   "1.4.0",
            "simulator": "http://localhost:8000/simulator",
            "websocket": "ws://localhost:8000/ws/trace"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")


@app.get("/simulator", response_class=HTMLResponse)
def serve_simulator():
    """
    Serves the MVC Live Trace Simulator directly from FastAPI.

    WHY: Opening the HTML file via file:// blocks WebSocket connections
    due to browser security (mixed content / origin restrictions).
    Serving it here puts everything on the same origin (localhost:8000)
    so WebSocket connects instantly and automatically.

    Usage:
        1. Start server:  uvicorn main:app --reload
        2. Open browser:  http://localhost:8000/simulator
        3. Open Swagger:  http://localhost:8000/docs
        4. Make a request in Swagger → Simulator animates automatically
    """
    # Look for the simulator HTML file next to main.py
    simulator_path = Path(__file__).parent / "mvc_simulator_3.html"

    if not simulator_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "mvc_simulator_3.html not found. "
                "Place it in the same folder as main.py."
            )
        )

    return HTMLResponse(content=simulator_path.read_text(encoding="utf-8"))