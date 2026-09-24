"""
Automatische Rechnungserstellung beim manuellen Freischalten einer Organization
(siehe app/routers/platform.py). Kein Stripe, keine automatisierte Zahlung –
nur die Rechnung selbst wird als PDF erzeugt und in R2 abgelegt, damit der
Betreiber sie im Admin-Dashboard herunterladen und selbst versenden kann.

Kleinunternehmerregelung (§ 19 UStG) ist der Standard, solange keine
USt-IdNr. hinterlegt ist (OWNER_VAT_ID env var) – sobald eine eingetragen
wird, weist die Rechnung stattdessen Umsatzsteuer aus.
"""
import os
from datetime import date, datetime, timezone
from decimal import Decimal

from fpdf import FPDF
from sqlalchemy.orm import Session

from app.models import Organization, Invoice, User
from app.services import storage_service

OWNER_NAME = "Mahmood AL-Djabboori"
OWNER_ADDRESS_LINES = ["Bokensdorfer Weg 21A", "38524 Sassenburg", "Deutschland"]
OWNER_EMAIL = "mahmood.aldjabboori@gmail.com"
PRICE_PER_EMPLOYEE_EUR = Decimal("12.00")
VAT_RATE = Decimal("0.19")


def _next_invoice_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    prefix = f"RE-{year}-"
    last = (
        db.query(Invoice)
        .filter(Invoice.invoice_number.like(f"{prefix}%"))
        .order_by(Invoice.invoice_number.desc())
        .first()
    )
    next_seq = int(last.invoice_number.split("-")[-1]) + 1 if last else 1
    return f"{prefix}{next_seq:04d}"


def _render_pdf(
    invoice_number: str, org: Organization, employee_count: int,
    unit_price: Decimal, net_total: Decimal, vat_amount: Decimal, gross_total: Decimal,
    period_start: date, period_end: date | None,
) -> bytes:
    owner_vat_id = os.getenv("OWNER_VAT_ID")

    pdf = FPDF(format="A4", unit="mm")
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Rechnung", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 5, OWNER_NAME, new_x="LMARGIN", new_y="NEXT")
    for line in OWNER_ADDRESS_LINES:
        pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, OWNER_EMAIL, new_x="LMARGIN", new_y="NEXT")
    if owner_vat_id:
        pdf.cell(0, 5, f"USt-IdNr.: {owner_vat_id}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    pdf.cell(0, 5, f"Rechnungsempfänger: {org.billing_contact_name or org.name}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, org.name, new_x="LMARGIN", new_y="NEXT")
    if org.billing_address:
        for line in org.billing_address.splitlines():
            pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    period_str = period_start.strftime("%d.%m.%Y") + " - " + (
        period_end.strftime("%d.%m.%Y") if period_end else "unbefristet"
    )
    pdf.cell(0, 5, f"Rechnungsnummer: {invoice_number}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Rechnungsdatum: {date.today().strftime('%d.%m.%Y')}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, f"Leistungszeitraum: {period_str}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(90, 7, "Leistung", border=1)
    pdf.cell(30, 7, "Menge", border=1, align="R")
    pdf.cell(35, 7, "Einzelpreis", border=1, align="R")
    pdf.cell(35, 7, "Gesamt", border=1, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", size=10)
    pdf.cell(90, 7, "OnboardGuide AI - Nutzung pro Mitarbeiter/Monat", border=1)
    pdf.cell(30, 7, str(employee_count), border=1, align="R")
    pdf.cell(35, 7, f"{unit_price:.2f} EUR", border=1, align="R")
    pdf.cell(35, 7, f"{net_total:.2f} EUR", border=1, align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.cell(155, 6, "Nettobetrag", align="R")
    pdf.cell(35, 6, f"{net_total:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    if owner_vat_id:
        pdf.cell(155, 6, f"zzgl. {int(VAT_RATE * 100)}% USt.", align="R")
        pdf.cell(35, 6, f"{vat_amount:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(155, 7, "Gesamtbetrag", align="R")
    pdf.cell(35, 7, f"{gross_total:.2f} EUR", align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(8)
    pdf.set_font("Helvetica", size=9)
    if not owner_vat_id:
        pdf.multi_cell(0, 5, "Gemäß § 19 UStG wird keine Umsatzsteuer berechnet (Kleinunternehmerregelung).")

    return bytes(pdf.output())


def create_invoice_for_activation(
    db: Session, org: Organization, period_start: date, period_end: date | None
) -> Invoice:
    employee_count = max(db.query(User).filter(User.organization_id == org.id).count(), 1)
    unit_price = PRICE_PER_EMPLOYEE_EUR
    net_total = unit_price * employee_count

    owner_vat_id = os.getenv("OWNER_VAT_ID")
    vat_amount = (net_total * VAT_RATE) if owner_vat_id else Decimal("0.00")
    gross_total = net_total + vat_amount

    invoice_number = _next_invoice_number(db)
    pdf_bytes = _render_pdf(
        invoice_number, org, employee_count, unit_price, net_total, vat_amount, gross_total,
        period_start, period_end,
    )

    storage_key = f"invoices/org_{org.id}/{invoice_number}.pdf"
    storage_service.upload_bytes(storage_key, pdf_bytes, content_type="application/pdf")

    invoice = Invoice(
        organization_id=org.id,
        invoice_number=invoice_number,
        period_start=period_start,
        period_end=period_end,
        employee_count=employee_count,
        unit_price_eur=unit_price,
        total_eur=gross_total,
        pdf_storage_key=storage_key,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
