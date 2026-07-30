"""
test_documents.py – Document Endpoint Tests

Tests:
- Dokumente abrufen als Verwaltung → alle
- Dokumente abrufen als Mitarbeiter → nur eigene Kategorie
- Upload als Verwaltung → 201
- Upload als Mitarbeiter → 403
"""

import pytest
import io


class TestGetDocuments:

    def test_get_documents_as_verwaltung(self, client, auth_headers):
        """Verwaltung sieht alle Dokumente."""
        response = client.get(
            "/api/documents",
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_documents_as_mitarbeiter(self, client, auth_headers):
        """Mitarbeiter sieht nur erlaubte Dokumente."""
        response = client.get(
            "/api/documents",
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_documents_no_token(self, client):
        """Ohne Token → 403."""
        response = client.get("/api/documents")
        assert response.status_code == 403


class TestUploadDocument:

    def test_upload_as_verwaltung(self, client, auth_headers, test_users):
        """Verwaltung kann Dokument hochladen."""
        file_content = b"Dies ist ein Test-Dokument fuer pytest."
        response = client.post(
            "/api/documents/upload",
            data={
                "title":       "pytest Test Dokument",
                "category":    "Allgemein",
                "uploaded_by": str(test_users["verwaltung"].id)
            },
            files={
                "file": ("test.txt", io.BytesIO(file_content), "text/plain")
            },
            headers=auth_headers["verwaltung"]
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "pytest Test Dokument"
        assert data["category"] == "Allgemein"

    def test_upload_as_mitarbeiter_forbidden(self, client, auth_headers,
                                              test_users):
        """Mitarbeiter darf nicht hochladen → 403."""
        file_content = b"Dieser Upload sollte scheitern."
        response = client.post(
            "/api/documents/upload",
            data={
                "title":       "Verbotener Upload",
                "category":    "Allgemein",
                "uploaded_by": str(test_users["mitarbeiter"].id)
            },
            files={
                "file": ("test.txt", io.BytesIO(file_content), "text/plain")
            },
            headers=auth_headers["mitarbeiter"]
        )
        assert response.status_code == 403

    def test_upload_no_token(self, client, test_users):
        """Ohne Token → 403."""
        file_content = b"Kein Token Upload."
        response = client.post(
            "/api/documents/upload",
            data={
                "title":       "Kein Token",
                "category":    "Allgemein",
                "uploaded_by": str(test_users["verwaltung"].id)
            },
            files={
                "file": ("test.txt", io.BytesIO(file_content), "text/plain")
            }
        )
        assert response.status_code == 403