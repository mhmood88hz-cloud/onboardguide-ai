from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.routers import auth, users, tasks, documents, chat

# Create all tables on startup if they don't exist yet
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="OnboardGuide AI Backend",
    description=(
        "Intelligent HR onboarding portal with RAG, conversation history, "
        "structured outputs, document upload, and role-based access control."
    ),
    version="1.3.0"
)

# Register all routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    """Health check – verifies database connection and server status."""
    try:
        db.execute(text("SELECT 1"))
        return {
            "status":   "online",
            "database": "onboardguide_db",
            "version":  "1.3.0"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")