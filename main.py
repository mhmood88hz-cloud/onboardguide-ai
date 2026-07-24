from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from pathlib import Path

from app.database import Base, engine, get_db
from app.routers import auth, users, tasks, documents, chat, ws
from app.services.ws_manager import manager

Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # Graceful shutdown – close all WebSocket connections
    for ws_conn in manager.active.copy():
        try:
            await ws_conn.close()
        except Exception:
            pass


app = FastAPI(
    title="OnboardGuide AI Backend",
    description="MVC modular design with Live Trace + RAG + Model Comparison.",
    version="1.5.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Workflow-Trace"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(ws.router)


@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {
            "status":    "online",
            "database":  "onboardguide_db",
            "version":   "1.5.0",
            "simulator": "http://localhost:8000/simulator",
            "websocket": "ws://localhost:8000/ws/trace"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB connection failed: {e}")


@app.get("/simulator", response_class=HTMLResponse)
def serve_simulator():
    simulator_path = Path(__file__).parent / "mvc_simulator_3.html"
    if not simulator_path.exists():
        raise HTTPException(
            status_code=404,
            detail="mvc_simulator_3.html not found next to main.py."
        )
    return HTMLResponse(content=simulator_path.read_text(encoding="utf-8"))