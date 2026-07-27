import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL = os.getenv("DATABASE_URL")

# Security
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Chat settings
CHAT_HISTORY_LIMIT = 5
# Chunking settings
CHUNK_SIZE    = 400   # tokens per chunk
CHUNK_OVERLAP = 50    # overlap between chunks
TOP_K_CHUNKS  = 3     # how many chunks to send to the model

# JWT settings
JWT_SECRET_KEY     = os.getenv("JWT_SECRET_KEY", "onboardguide-secret-2026")
JWT_ALGORITHM      = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))