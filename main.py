import os
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()


DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
sessionlocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
app = FastAPI(title="OnboardGuide AI Backend")

def get_db():# -> Session:
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def check_connection(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "online",
                "message": "Database connection successful",
                "database": "OnboardGuide AI"
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed {str(e)}")

