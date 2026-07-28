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

```
graph TB
    subgraph Client["Client Layer"]
        Swagger["Swagger UI (/docs)"]
        Simulator["Live Trace Simulator (/simulator)"]
    end

    subgraph Backend["Backend (FastAPI)"]
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
            AI["ai_service.py — RAG + Model Comparison"]
            Chunk["chunking_service.py — Text → Chunks → Embeddings"]
            Trace["trace.py — Live Trace Recording"]
            WSM["ws_manager.py — WebSocket Broadcast"]
        end

        subgraph Shared["Shared"]
            Config["config.py"]
            Security["security.py — JWT + bcrypt"]
            Schema["schemas.py — Pydantic"]
            DB["database.py — SQLAlchemy"]
        end
    end

    subgraph Database["Database Layer"]
        PG[("PostgreSQL + pgvector")]
    end

    subgraph AI_External["External AI"]
        OpenAI["OpenAI API"]
    end

    Swagger --> Main
    Main --> Routers
    Routers --> Services
    Services --> PG
    Services --> OpenAI
    WSM --> Simulator
```

---

## Database

```
erDiagram
    users ||--o{ tasks : assigned_to
    users ||--o{ chat_messages : user_id
    users ||--o{ documents : uploaded_by
    documents ||--o{ document_chunks : document_id

    users {
        INT id
        TEXT username
        TEXT email
        TEXT password_hash
        TEXT user_role
        TEXT department
        TEXT assigned_project
        INT reports_to
        INT progress_percent
    }

    documents {
        INT id
        TEXT title
        TEXT filepath
        TEXT content
        TEXT category
        INT uploaded_by
    }

    document_chunks {
        INT id
        INT document_id
        INT chunk_index
        TEXT content
        VECTOR embedding
        INT token_count
        JSONB chunk_metadata
    }

    tasks {
        INT id
        TEXT title
        TEXT task_type
        INT assigned_to
        INT assigned_by
        BOOL is_completed
        TIMESTAMP completed_at
    }

    chat_messages {
        INT id
        INT user_id
        TEXT user_question
        TEXT ai_response
    }
```

---

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

- [x] MVC modularization (784 → 35 lines main.py)
- [x] RAG with pgvector + chunking (text-embedding-3-small)
- [x] JWT authentication (login / register / change-password)
- [x] Role-based access control (Verwaltung / Leader / Mitarbeiter)
- [x] Live Trace Simulator with WebSocket (auto-animation)
- [x] Model comparison (gpt-4o-mini vs gpt-5-mini — time, tokens, cost)
- [x] Structured Outputs (task explainer)
- [x] Password change / reset endpoints

### 🔜 Planned

- [ ] Frontend with React (Figma design)
- [ ] Alembic database migrations
- [ ] pytest automated tests
- [ ] Docker containerization
- [ ] Azure OpenAI for sensitive data (private deployment)

---

## About

**1:1 GenAI Mentoring Program**
Mentor: Fares | Developer: Mahmood Al-Djabboori****