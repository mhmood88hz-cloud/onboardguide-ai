"""
test_templates.py – Onboarding-Vorlagen Endpoint Tests

Tests:
- Vorlage erstellen (Verwaltung) → 201, Items enthalten
- Vorlage erstellen als Nicht-Verwaltung → 403
- Vorlagen auflisten → 200
- Vorlage anwenden bei Registrierung → neue Aufgaben werden automatisch angelegt
- Registrierung mit ungültiger template_id → 404
- Vorlage löschen → 204, danach nicht mehr in der Liste
"""

import pytest


class TestCreateTemplate:

    def test_create_template_success(self, client, auth_headers):
        response = client.post("/api/templates", json={
            "name": "pytest IT-Onboarding",
            "department": "IT",
            "items": [
                {"title": "pytest VPN einrichten", "task_type": "Onboarding"},
                {"title": "pytest Laptop abholen", "description": "Bei IT-Support", "task_type": "Onboarding"},
            ],
        }, headers=auth_headers["verwaltung"])
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "pytest IT-Onboarding"
        assert len(data["items"]) == 2
        assert data["items"][0]["title"] == "pytest VPN einrichten"

    def test_create_template_forbidden_for_mitarbeiter(self, client, auth_headers):
        response = client.post("/api/templates", json={
            "name": "pytest Verbotene Vorlage",
            "items": [{"title": "pytest Irgendwas"}],
        }, headers=auth_headers["mitarbeiter"])
        assert response.status_code == 403


class TestListTemplates:

    def test_list_templates(self, client, auth_headers):
        client.post("/api/templates", json={
            "name": "pytest Listen-Vorlage",
            "items": [{"title": "pytest Schritt 1"}],
        }, headers=auth_headers["verwaltung"])

        response = client.get("/api/templates", headers=auth_headers["verwaltung"])
        assert response.status_code == 200
        names = [t["name"] for t in response.json()]
        assert "pytest Listen-Vorlage" in names


class TestApplyTemplateOnRegister:

    def test_register_with_template_creates_tasks(self, client, auth_headers, db_session, test_org):
        create_res = client.post("/api/templates", json={
            "name": "pytest Anwenden-Vorlage",
            "items": [
                {"title": "pytest Task A"},
                {"title": "pytest Task B", "description": "Zweiter Schritt"},
            ],
        }, headers=auth_headers["verwaltung"])
        template_id = create_res.json()["id"]

        register_res = client.post("/api/auth/register", json={
            "username": "test_neuer_mitarbeiter",
            "email": "neuer.mitarbeiter@test.de",
            "password": "password123",
            "user_role": "Mitarbeiter",
            "template_id": template_id,
        }, headers=auth_headers["verwaltung"])
        assert register_res.status_code == 201
        new_user_id = register_res.json()["id"]

        tasks_res = client.get(f"/api/tasks?user_id={new_user_id}", headers=auth_headers["verwaltung"])
        assert tasks_res.status_code == 200
        titles = {t["title"] for t in tasks_res.json()}
        assert titles == {"pytest Task A", "pytest Task B"}

    def test_register_with_invalid_template_id(self, client, auth_headers):
        response = client.post("/api/auth/register", json={
            "username": "test_ungueltige_vorlage",
            "email": "ungueltig@test.de",
            "password": "password123",
            "user_role": "Mitarbeiter",
            "template_id": 999999,
        }, headers=auth_headers["verwaltung"])
        assert response.status_code == 404


class TestDeleteTemplate:

    def test_delete_template(self, client, auth_headers):
        create_res = client.post("/api/templates", json={
            "name": "pytest Löschen-Vorlage",
            "items": [{"title": "pytest Wird gelöscht"}],
        }, headers=auth_headers["verwaltung"])
        template_id = create_res.json()["id"]

        delete_res = client.delete(f"/api/templates/{template_id}", headers=auth_headers["verwaltung"])
        assert delete_res.status_code == 204

        list_res = client.get("/api/templates", headers=auth_headers["verwaltung"])
        ids = [t["id"] for t in list_res.json()]
        assert template_id not in ids
