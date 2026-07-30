# OnboardGuide AI 🤖

> *From Latin "onboarding" (Einarbeitung) and German "Leitfaden" (guide) — OnboardGuide AI is an intelligent HR onboarding assistant that meets new employees where they are: answering real questions from real company documents, not generic tutorials.*

Upload company policies, project plans, and handbooks. OnboardGuide extracts relevant context, builds a personal knowledge base per role, and lets employees chat with an AI that knows exactly what documents they are allowed to see.

---

## What it does

| | |
|---|---|
| **RAG with pgvector** | Documents are chunked, embedded and stored as vectors for precise retrieval |
| **Role-based access** | Verwaltung / Leader / Mitarbeiter each see only their permitted documents |
| **JWT Authentication** | Secure login — every action is tied to a real identity |
| **Model comparison** | gpt-4o-mini vs gpt-5-mini — response time, tokens, cost side by side |
| **Live Trace Simulator** | Every API request animates the MVC data flow automatically via WebSocket |
| **Structured Outputs** | Task explainer returns guaranteed JSON: summary + steps + tips |

---

## Endpoints

### Auth

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/login` | – | Login → JWT Token |
| `POST` | `/api/auth/register` | JWT + Verwaltung | Register new employee |
| `POST` | `/api/auth/change-password` | JWT | Change own password |
| `POST` | `/api/auth/reset-password` | JWT + Verwaltung | Reset any user's password |

### Users

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `DELETE` | `/api/users/{id}` | JWT + Verwaltung | Delete user (cascade) |

### Documents

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/documents/upload` | JWT + Verwaltung | Upload PDF/TXT → chunk → embed |
| `GET` | `/api/documents` | JWT | List documents (role-filtered) |

### Tasks

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/tasks` | – | Create task |
| `GET` | `/api/tasks` | – | Get user tasks |
| `PUT` | `/api/tasks/{id}/complete` | JWT | Complete task (RBAC check) |
| `GET` | `/api/tasks/leader/progress` | – | Team progress |

### Chat

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/chat/ask` | JWT | RAG chat with similarity scores |
| `POST` | `/api/chat/tasks/{id}/explain` | JWT | Task explainer (Structured Outputs) |

### System

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/` | – | Health check |
| `GET` | `/simulator` | – | MVC Live Trace Simulator |
| `WS` | `/ws/trace` | – | WebSocket trace stream |

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend | FastAPI + Python 3.12 |
| Database | PostgreSQL 18 + pgvector 0.8.3 |
| ORM | SQLAlchemy |
| Validation | Pydantic v2 |
| Auth | JWT (python-jose) + bcrypt |
| LLM | OpenAI gpt-4o-mini / gpt-5-mini |
| Embeddings | text-embedding-3-small (1536 dim) |
| Real-time | WebSocket (uvicorn[standard]) |

---

## Getting Started

### Database

Install PostgreSQL 18 and create the database:

```sql
CREATE DATABASE onboardguide_db;
```

Install pgvector extension:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# → Fill in DATABASE_URL, OPENAI_API_KEY, JWT_SECRET_KEY, ADMIN_TOKEN

# Start server
uvicorn main:app --reload
```

### Simulator

Open in browser after starting the server:

```
http://localhost:8000/simulator
```

Make any request in Swagger UI — the simulator animates automatically.

---

## Environment Variables

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/onboardguide_db
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini
JWT_SECRET_KEY=your-long-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=480
ADMIN_TOKEN=your-admin-token
CHUNK_SIZE=400
CHUNK_OVERLAP=50
TOP_K_CHUNKS=3
```

---

## Architecture

```mermaid
graph TB
    subgraph Client["Client Layer"]
        Swagger["Swagger UI (/docs)"]
        Simulator["Live Trace Simulator (/simulator)"]
    end

    subgraph Backend["Backend (FastAPI + Python 3.12)"]
        Main["main.py — Entry Point (35 lines)"]

        subgraph Routers["Controller Layer (routers/)"]
            Auth["auth.py"]
            Users["users.py"]
            Tasks["tasks.py"]
            Docs["documents.py"]
            Chat["chat.py"]
            WS["ws.py"]
        end

        subgraph Services["Service Layer (services/)"]
            AI["ai_service.py"]
            Chunk["chunking_service.py"]
            Trace["trace.py"]
            WSM["ws_manager.py"]
        end

        subgraph Shared["Shared"]
            Config["config.py"]
            Security["security.py"]
            Schema["schemas.py"]
            DB["database.py"]
        end
    end

    subgraph Database["Database Layer"]
        PG[("PostgreSQL + pgvector")]
    end

    subgraph External["External AI"]
        OpenAI["OpenAI API"]
    end

    Swagger --> Main
    Simulator -->|WebSocket| WS
    Main --> Routers
    Routers --> Services
    Routers --> Shared
    Services --> PG
    Services --> OpenAI
    WSM --> Simulator
```

---

## Database

```mermaid
erDiagram
    users ||--o{ tasks : "assigned_to"
    users ||--o{ chat_messages : "user_id"
    users ||--o{ documents : "uploaded_by"
    documents ||--o{ document_chunks : "document_id"

    users {
        int id PK
        string username
        string email
        string password_hash
        string user_role
        string department
        string assigned_project
        int reports_to FK
        int progress_percent
    }

    documents {
        int id PK
        string title
        string filepath
        string content
        string category
        int uploaded_by FK
    }

    document_chunks {
        int id PK
        int document_id FK
        int chunk_index
        string content
        vector embedding
        int token_count
        jsonb chunk_metadata
    }

    tasks {
        int id PK
        string title
        string task_type
        int assigned_to FK
        int assigned_by FK
        boolean is_completed
        timestamp completed_at
    }

    chat_messages {
        int id PK
        int user_id FK
        string user_question
        string ai_response
    }
```

## The Three RAG Pillars

```
Pillar A — Conversation History
  Last 5 messages from DB → model remembers context

Pillar B — Dynamic Context Injection
  System prompt with role/department/project → personalized answers

Pillar C — Vector RAG (pgvector)
  Question → embedding → cosine search → top-3 chunks → model
```

---

## Role Concept

| Role | Permissions |
|---|---|
| **Verwaltung** | All documents, register users, upload, delete |
| **Leader** | Own department + team documents, manage tasks |
| **Mitarbeiter** | Own documents, own tasks, chat |

---

## Roadmap

### ✅ Done

- [x] Initial project setup (DB, Backend, Swagger UI)
- [x] SQLAlchemy models & Pydantic schemas
- [x] Role system (Verwaltung / Leader / Mitarbeiter)
- [x] Admin token authentication (first implementation)
- [x] User registration & deletion (Verwaltung only)
- [x] Document upload with role-based access control
- [x] Task management with ownership validation (RBAC)
- [x] OpenAI integration (gpt-4o-mini / gpt-5-mini)
- [x] Three prompt engineering pillars (History · Context · RAG)
- [x] Structured Outputs for task explainer
- [x] MVC modularization (784 → 35 lines main.py)
- [x] Live Trace Simulator with WebSocket (auto-animation)
- [x] RAG upgraded to pgvector + chunking (text-embedding-3-small)
- [x] Model comparison with metrics (time, tokens, cost)
- [x] **JWT authentication** — replaced admin token after security review
  - Admin token: anyone who knew the token could act as any user
  - JWT: requires real login, cryptographically signed, role verified
- [x] Password change & reset endpoints
- [x] README with Mermaid architecture + ER diagrams

### 🔜 Planned

- [ ] Frontend with React (Figma design first)
- [ ] pytest automated tests
- [ ] Local model support (ollama + sentence-transformers) for sensitive documents
- [ ] Alembic database migrations
- [ ] Docker containerization
---
## Privacy & Sensitive Data

OnboardGuide AI currently sends document chunks to the OpenAI API for embedding and chat completion.
This is suitable for general company knowledge (policies, handbooks, project guidelines).

For sensitive data that must not leave the internal network, the planned approach is a **local model deployment**:

### Local Embeddings + Local LLM (fully offline)

```
Document → local embedding model     ← sentence-transformers
         → pgvector stores vectors   ← same PostgreSQL
         → ollama answers locally    ← no data leaves network
```

**Tools:**
- `ollama` – run llama3, mistral, phi3 locally on your own server
- `sentence-transformers` – local embeddings without OpenAI
- Everything stays on your own infrastructure

### Planned Implementation

A `is_sensitive` flag on the `documents` table will control routing:

```python
if document.is_sensitive:
    embedding = local_embed(chunk)    # sentence-transformers (offline)
else:
    embedding = openai_embed(chunk)   # OpenAI API (current)
```

Sensitive documents (salary data, customer contracts, internal strategies)
never leave the internal network. General onboarding content continues
to use the faster OpenAI pipeline.
---
## About

**1:1 GenAI Mentoring Program**
Mentor: Fares | Developer: Mahmood Al-Djabboori****
