"""
test_auth.py – Authentication Endpoint Tests

Tests:
- Login mit richtigen Daten → Token
- Login mit falschem Passwort → 401
- Login mit unbekanntem User → 401
- Passwort ändern → 200
- Passwort ändern mit falschem altem Passwort → 400
- Register als Verwaltung → 201
- Register als Mitarbeiter → 403
"""

import pytest


class TestLogin:

    def test_login_success(self, client, test_users):
        """Erfolgreicher Login gibt JWT Token zurück."""
        response = client.post("/api/auth/login", json={
            "username": "test_sarah",
            "password": "password123"
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["username"] == "test_sarah"
        assert data["user_role"] == "Verwaltung"

    def test_login_wrong_password(self, client):
        """Falsches Passwort → 401 Unauthorized."""
        response = client.post("/api/auth/login", json={
            "username": "test_sarah",
            "password": "falsches_passwort"
        })
        assert response.status_code == 401
        assert "falsch" in response.json()["detail"].lower()

    def test_login_unknown_user(self, client):
        """Unbekannter Benutzername → 401 Unauthorized."""
        response = client.post("/api/auth/login", json={
            "username": "existiert_nicht",
            "password": "password123"
        })
        assert response.status_code == 401

    def test_login_returns_correct_role(self, client):
        """Login gibt die korrekte Rolle zurück."""
        response = client.post("/api/auth/login", json={
            "username": "test_lisa",
            "password": "password123"
        })
        assert response.status_code == 200
        assert response.json()["user_role"] == "Mitarbeiter"


class TestChangePassword:

    def test_change_password_success(self, client, auth_headers):
        """Mitarbeiter kann eigenes Passwort ändern."""
        response = client.post("/api/auth/change-password",
            json={
                "old_password": "password123",
                "new_password": "NeuesPasswort2026!"
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200
        assert "erfolgreich" in response.json()["message"].lower()

        # Zurücksetzen für andere Tests
        client.post("/api/auth/change-password",
            json={
                "old_password": "NeuesPasswort2026!",
                "new_password": "password123"
            },
            headers=auth_headers["mitarbeiter"]
        )

    def test_change_password_wrong_old(self, client, auth_headers):
        """Falsches altes Passwort → 400."""
        response = client.post("/api/auth/change-password",
            json={
                "old_password": "falsches_altes_passwort",
                "new_password": "NeuesPasswort2026!"
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 400

    def test_change_password_no_token(self, client):
        """Ohne Token → 403."""
        response = client.post("/api/auth/change-password",
            json={
                "old_password": "password123",
                "new_password": "NeuesPasswort2026!"
            }
        )
        assert response.status_code == 403


class TestRegister:

    def test_register_as_verwaltung(self, client, auth_headers):
        """Verwaltung kann neuen Benutzer registrieren."""
        response = client.post("/api/auth/register",
            json={
                "username": "neuer_mitarbeiter",
                "email": "neu@test.de",
                "password": "password123",
                "user_role": "Mitarbeiter",
                "department": "IT"
            },
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 201
        assert response.json()["username"] == "neuer_mitarbeiter"
        assert "password_hash" not in response.json()

    def test_register_as_mitarbeiter_forbidden(self, client, auth_headers):
        """Mitarbeiter darf nicht registrieren → 403."""
        response = client.post("/api/auth/register",
            json={
                "username": "unerlaubt",
                "email": "unerlaubt@test.de",
                "password": "password123",
                "user_role": "Mitarbeiter"
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 403

    def test_register_duplicate_username(self, client, auth_headers):
        """Doppelter Benutzername → 400."""
        response = client.post("/api/auth/register",
            json={
                "username": "test_sarah",
                "email": "andere@test.de",
                "password": "password123",
                "user_role": "Mitarbeiter"
            },
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 400

    def test_register_no_token(self, client):
        """Ohne Token → 403."""
        response = client.post("/api/auth/register",
            json={
                "username": "kein_token",
                "email": "kein@test.de",
                "password": "password123",
                "user_role": "Mitarbeiter"
            }
        )
        assert response.status_code == 403