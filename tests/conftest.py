import os
import pytest

# ── MUSS ALLERERSTE ZEILEN SEIN ───────────────────────────────────────────
from sqlalchemy.engine import URL as SA_URL

# Produktions-DB URL für app imports
_prod_url = SA_URL.create(
    drivername="postgresql+psycopg",
    username="postgres",
    password="postgreMila5",
    host="localhost",
    port=5432,
    database="onboardguide_db"
)
os.environ["DATABASE_URL"] = _prod_url.render_as_string(hide_password=False)

# ── App imports NACH os.environ ───────────────────────────────────────────
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.security import hash_password, create_access_token
from app.models import User, Task
from main import app

# ── Test DB ───────────────────────────────────────────────────────────────
_test_url = SA_URL.create(
    drivername="postgresql+psycopg",
    username="postgres",
    password="postgreMila5",
    host="localhost",
    port=5432,
    database="onboardguide_test_db"
)

engine_test = create_engine(_test_url)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    with engine_test.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine_test)
    yield
    with engine_test.connect() as conn:
        conn.execute(text("DELETE FROM chat_messages WHERE user_id IN (SELECT id FROM users WHERE username LIKE 'test_%')"))
        conn.execute(text("DELETE FROM tasks WHERE title LIKE '%pytest%' OR title LIKE '%Test Task%' OR title LIKE '%Fremder%' OR title LIKE '%Verwaltung Test%' OR title LIKE '%Neuer Test%'"))
        conn.execute(text("DELETE FROM document_chunks WHERE document_id IN (SELECT id FROM documents WHERE title LIKE '%pytest%')"))
        conn.execute(text("DELETE FROM documents WHERE title LIKE '%pytest%'"))
        conn.execute(text("DELETE FROM users WHERE username LIKE 'test_%' OR username = 'neuer_mitarbeiter' OR username = 'unerlaubt'"))
        conn.commit()


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="session")
def test_users(db_session):
    verwaltung = User(username="test_sarah", email="sarah@test.de",
                      password_hash=hash_password("password123"),
                      user_role="Verwaltung", department="HR")
    leader = User(username="test_max", email="max@test.de",
                  password_hash=hash_password("password123"),
                  user_role="Leader", department="IT")
    mitarbeiter = User(username="test_lisa", email="lisa@test.de",
                       password_hash=hash_password("password123"),
                       user_role="Mitarbeiter", department="IT")
    db_session.add_all([verwaltung, leader, mitarbeiter])
    db_session.commit()
    for u in [verwaltung, leader, mitarbeiter]:
        db_session.refresh(u)
    mitarbeiter.reports_to = leader.id
    db_session.commit()
    return {"verwaltung": verwaltung, "leader": leader, "mitarbeiter": mitarbeiter}


@pytest.fixture(scope="session")
def tokens(test_users):
    return {
        "verwaltung": create_access_token(user_id=test_users["verwaltung"].id,
                                          username=test_users["verwaltung"].username,
                                          role="Verwaltung"),
        "leader": create_access_token(user_id=test_users["leader"].id,
                                      username=test_users["leader"].username,
                                      role="Leader"),
        "mitarbeiter": create_access_token(user_id=test_users["mitarbeiter"].id,
                                           username=test_users["mitarbeiter"].username,
                                           role="Mitarbeiter"),
    }


@pytest.fixture(scope="session")
def auth_headers(tokens):
    return {
        "verwaltung":  {"Authorization": f"Bearer {tokens['verwaltung']}"},
        "leader":      {"Authorization": f"Bearer {tokens['leader']}"},
        "mitarbeiter": {"Authorization": f"Bearer {tokens['mitarbeiter']}"},
    }


@pytest.fixture(scope="session")
def test_task(db_session, test_users):
    task = Task(title="Test Task pytest", description="Test",
                task_type="Onboarding",
                assigned_to=test_users["mitarbeiter"].id,
                assigned_by=test_users["verwaltung"].id,
                is_completed=False)
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task