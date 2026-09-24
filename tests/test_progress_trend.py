"""
test_progress_trend.py – GET /api/tasks/progress-trend

Tests:
- Trend für User mit erledigten Aufgaben → letzter Punkt spiegelt aktuellen Fortschritt wider
- Trend für User ohne Aufgaben → alle Punkte 0%
- Fremder User in anderer Firma → 404
"""

from datetime import date, timedelta


class TestProgressTrend:

    def test_trend_reflects_current_progress(self, client, auth_headers, test_users, db_session):
        create_res = client.post("/api/tasks", json={
            "title": "pytest Trend Task 1", "task_type": "Onboarding",
            "assigned_to": test_users["mitarbeiter"].id,
        }, headers=auth_headers["verwaltung"])
        task_id = create_res.json()["id"]
        client.put(f"/api/tasks/{task_id}/complete", headers=auth_headers["verwaltung"])

        response = client.get(
            f"/api/tasks/progress-trend?user_id={test_users['mitarbeiter'].id}&days=7",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200
        data = response.json()
        # Der mitarbeiter-Fixture ist session-weit geteilt – andere Testdateien legen ggf.
        # weitere (unerledigte) Tasks für denselben User an, daher hier relativ statt fix 100%
        # prüfen (mind. der gerade erledigte Task zählt).
        assert len(data["points"]) == 7
        assert data["points"][-1]["date"] == str(date.today())
        expected_percent = round(data["completed_tasks"] / data["total_tasks"] * 100)
        assert data["points"][-1]["completed_percent"] == expected_percent
        assert data["total_tasks"] >= 1
        assert data["completed_tasks"] >= 1

    def test_trend_for_user_without_tasks(self, client, auth_headers, test_org, db_session):
        from app.models import User
        from app.security import hash_password

        empty_user = User(username="test_leer", email="leer@test.de",
                          password_hash=hash_password("password123"),
                          user_role="Mitarbeiter", organization_id=test_org.id)
        db_session.add(empty_user)
        db_session.commit()
        db_session.refresh(empty_user)

        response = client.get(
            f"/api/tasks/progress-trend?user_id={empty_user.id}&days=5",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200
        data = response.json()
        assert all(p["completed_percent"] == 0 for p in data["points"])
        assert data["total_tasks"] == 0

    def test_trend_for_foreign_user_not_found(self, client, auth_headers):
        response = client.get(
            "/api/tasks/progress-trend?user_id=999999&days=7",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 404
