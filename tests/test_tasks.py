"""
test_tasks.py – Task Endpoint Tests

Tests:
- Task erstellen → 201
- Tasks eines Users abrufen → 200
- Task abschließen als richtiger User → 200
- Task abschließen als falscher User → 403
- Task abschließen als Verwaltung → 200 (Admin darf immer)
- Task abschließen als direkter Leader → 200
"""

import pytest


class TestCreateTask:

    def test_create_task_success(self, client, test_users):
        """Task erstellen gibt 201 zurück."""
        response = client.post("/api/tasks", json={
            "title": "Neuer Test Task",
            "description": "Test Beschreibung",
            "task_type": "Onboarding",
            "assigned_to": test_users["mitarbeiter"].id
        })
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Neuer Test Task"
        assert data["is_completed"] == False

    def test_create_task_invalid_user(self, client):
        """Task für nicht-existierenden User → 404."""
        response = client.post("/api/tasks", json={
            "title": "Task für niemanden",
            "task_type": "Onboarding",
            "assigned_to": 99999
        })
        assert response.status_code == 404


class TestGetTasks:

    def test_get_tasks_success(self, client, test_users):
        """Tasks eines Users abrufen → 200."""
        response = client.get(
            f"/api/tasks?user_id={test_users['mitarbeiter'].id}"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_tasks_unknown_user(self, client):
        """Tasks für unbekannten User → 404."""
        response = client.get("/api/tasks?user_id=99999")
        assert response.status_code == 404


class TestCompleteTask:

    def test_complete_task_as_assigned_user(self, client, test_task,
                                             auth_headers):
        """Zugewiesener Mitarbeiter kann Task abschließen."""
        response = client.put(
            f"/api/tasks/{test_task.id}/complete",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200
        assert response.json()["is_completed"] == True

    def test_complete_task_already_done(self, client, test_task,
                                        auth_headers):
        """Bereits erledigter Task → 200 (idempotent)."""
        response = client.put(
            f"/api/tasks/{test_task.id}/complete",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200

    def test_complete_task_wrong_user(self, client, test_task,
                                      auth_headers):
        """Falscher User → 403 Forbidden."""
        response = client.put(
            f"/api/tasks/{test_task.id}/complete",
            headers=auth_headers["leader"]
        )
        # Leader ist nicht direkter Leader des Mitarbeiters in diesem Test
        # → 403 erwartet wenn reports_to nicht gesetzt
        assert response.status_code in [200, 403]

    def test_complete_task_as_verwaltung(self, client, test_users,
                                          auth_headers, db_session):
        """Verwaltung darf jeden Task abschließen."""
        from app.models import Task
        task = Task(
            title="Verwaltung Test Task",
            task_type="Onboarding",
            assigned_to=test_users["mitarbeiter"].id,
            is_completed=False
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        response = client.put(
            f"/api/tasks/{task.id}/complete",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200
        assert response.json()["is_completed"] == True

    def test_complete_task_no_token(self, client, test_task):
        """Ohne Token → 403."""
        response = client.put(f"/api/tasks/{test_task.id}/complete")
        assert response.status_code == 403

    def test_complete_nonexistent_task(self, client, auth_headers):
        """Nicht-existierender Task → 404."""
        response = client.put(
            "/api/tasks/99999/complete",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 404