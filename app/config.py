import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL as SA_URL

load_dotenv()

# Database – URL sicher gebaut wegen @ im Passwort
DATABASE_URL = SA_URL.create(
    drivername="postgresql+psycopg",  # ← psycopg3
    username=os.getenv("DB_USER", "postgres"),
    password=os.getenv("DB_PASSWORD", "postgreMila5"),  # ← kein @
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "5432")),
    database=os.getenv("DB_NAME", "onboardguide_db")
).render_as_string(hide_password=False)

# Security
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Chat settings
CHAT_HISTORY_LIMIT = 5

# Chunking settings
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50
TOP_K_CHUNKS  = 3

# JWT settings
JWT_SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "onboardguide-secret-2026")
JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))