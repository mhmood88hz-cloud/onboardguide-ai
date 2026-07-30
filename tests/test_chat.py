"""
test_chat.py – Chat Endpoint Tests

Tests:
- RAG Chat mit gültigem Token → 200 + Antwort
- RAG Chat ohne Token → 403
- RAG Chat gibt chunk_stats zurück
- Task Erklärer mit eigenem Task → 200
- Task Erklärer mit fremdem Task als Mitarbeiter → 403
- Task Erklärer ohne Token → 403
"""

import pytest


class TestRagChat:

    def test_chat_success(self, client, auth_headers):
        """RAG Chat gibt Antwort zurück."""
        response = client.post(
            "/api/chat/ask",
            json={
                "question": "Was sind die Onboarding-Schritte?",
                "compare_models": False
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "ai_response" in data
        assert "user_question" in data
        assert "used_documents" in data
        assert "chunk_stats" in data
        assert isinstance(data["chunk_stats"], list)

    def test_chat_no_token(self, client):
        """Ohne Token → 403."""
        response = client.post(
            "/api/chat/ask",
            json={
                "question": "Test Frage",
                "compare_models": False
            }
        )
        assert response.status_code == 403

    def test_chat_empty_question(self, client, auth_headers):
        """Leere Frage → 422 Validation Error."""
        response = client.post(
            "/api/chat/ask",
            json={
                "question": "",
                "compare_models": False
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 422

    def test_chat_as_verwaltung(self, client, auth_headers):
        """Verwaltung sieht alle Dokumente im RAG."""
        response = client.post(
            "/api/chat/ask",
            json={
                "question": "Was sind die IT-Sicherheitsrichtlinien?",
                "compare_models": False
            },
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200
        assert len(response.json()["ai_response"]) > 0

    def test_chat_saves_to_history(self, client, auth_headers, db_session):
        """Chat-Verlauf wird in chat_messages gespeichert."""
        from app.models import ChatMessage

        question = "pytest History Test Frage"
        client.post(
            "/api/chat/ask",
            json={"question": question, "compare_models": False},
            headers=auth_headers["mitarbeiter"]
        )

        saved = db_session.query(ChatMessage).filter(
            ChatMessage.user_question == question
        ).first()

        assert saved is not None
        assert saved.ai_response is not None


class TestTaskExplainer:

    def test_explain_own_task(self, client, auth_headers, test_task):
        """Mitarbeiter kann eigenen Task erklären lassen."""
        response = client.post(
            f"/api/chat/tasks/{test_task.id}/explain",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert "explanation" in data
        assert "summary" in data["explanation"]
        assert "steps" in data["explanation"]
        assert "tools_and_tips" in data["explanation"]
        assert isinstance(data["explanation"]["steps"], list)

    def test_explain_foreign_task_as_mitarbeiter(self, client, auth_headers,
                                                   db_session, test_users):
        """Mitarbeiter darf fremden Task nicht erklären → 403."""
        from app.models import Task
        other_task = Task(
            title="Fremder Task",
            task_type="Onboarding",
            assigned_to=test_users["leader"].id,
            is_completed=False
        )
        db_session.add(other_task)
        db_session.commit()
        db_session.refresh(other_task)

        response = client.post(
            f"/api/chat/tasks/{other_task.id}/explain",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 403

    def test_explain_as_verwaltung(self, client, auth_headers, test_task):
        """Verwaltung darf jeden Task erklären."""
        response = client.post(
            f"/api/chat/tasks/{test_task.id}/explain",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200

    def test_explain_nonexistent_task(self, client, auth_headers):
        """Nicht-existierender Task → 404."""
        response = client.post(
            "/api/chat/tasks/99999/explain",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 404

    def test_explain_no_token(self, client, test_task):
        """Ohne Token → 403."""
        response = client.post(
            f"/api/chat/tasks/{test_task.id}/explain"
        )
        assert response.status_code == 403