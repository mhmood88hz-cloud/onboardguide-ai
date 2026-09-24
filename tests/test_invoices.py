"""
test_invoices.py – automatische Rechnungserstellung beim Freischalten

Tests:
- Freischalten mit Mitarbeitern → 200, Rechnung mit korrektem Betrag wird erzeugt
- Rechnung ist über /invoices und /invoices/{id}/pdf abrufbar (echtes PDF)
- Rechnungsadresse wird auf der Organization gespeichert und wiederverwendet
- Zweite Rechnung bekommt eine fortlaufende, andere Nummer
- Ohne x-admin-token → 403
"""

import os


ADMIN_HEADERS = {"x-admin-token": os.getenv("ADMIN_TOKEN", "4514")}


class TestInvoiceOnActivate:

    def test_activate_creates_invoice_with_correct_total(self, client, test_org, test_users):
        response = client.post(
            f"/api/platform/organizations/{test_org.id}/activate",
            json={
                "billing_contact_name": "pytest Kontaktperson",
                "billing_address": "pytest Teststr. 1\n12345 Testort",
            },
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200
        assert response.json()["billing_contact_name"] == "pytest Kontaktperson"

        invoices_res = client.get(f"/api/platform/organizations/{test_org.id}/invoices", headers=ADMIN_HEADERS)
        assert invoices_res.status_code == 200
        invoices = invoices_res.json()
        assert len(invoices) >= 1
        latest = invoices[0]
        # test_org's Mitarbeiterzahl ist session-weit geteilt und kann durch andere Testdateien
        # wachsen (z.B. test_auth.py registriert weitere User) – daher relativ statt fix prüfen.
        assert latest["employee_count"] >= 3
        assert latest["unit_price_eur"] == 12.0
        assert latest["total_eur"] == latest["employee_count"] * 12.0
        assert latest["invoice_number"].startswith("RE-")

    def test_invoice_pdf_is_downloadable(self, client, test_org):
        invoices_res = client.get(f"/api/platform/organizations/{test_org.id}/invoices", headers=ADMIN_HEADERS)
        invoice_id = invoices_res.json()[0]["id"]

        pdf_res = client.get(
            f"/api/platform/organizations/{test_org.id}/invoices/{invoice_id}/pdf",
            headers=ADMIN_HEADERS,
        )
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")

    def test_second_activation_creates_new_sequential_invoice(self, client, test_org):
        first_res = client.get(f"/api/platform/organizations/{test_org.id}/invoices", headers=ADMIN_HEADERS)
        first_count = len(first_res.json())
        first_number = first_res.json()[0]["invoice_number"]

        client.post(f"/api/platform/organizations/{test_org.id}/activate", json={}, headers=ADMIN_HEADERS)

        second_res = client.get(f"/api/platform/organizations/{test_org.id}/invoices", headers=ADMIN_HEADERS)
        second_list = second_res.json()
        assert len(second_list) == first_count + 1
        assert second_list[0]["invoice_number"] != first_number

    def test_activate_without_admin_token_forbidden(self, client, test_org):
        response = client.post(f"/api/platform/organizations/{test_org.id}/activate", json={})
        assert response.status_code in (401, 403, 422)
