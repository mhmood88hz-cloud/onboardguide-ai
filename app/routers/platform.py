from datetime import date, timedelta
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Organization, Invoice
from app.schemas import OrganizationAdminResponse, ActivateOrganizationRequest, InvoiceResponse
from app.security import verify_admin_token
from app.services import storage_service
from app.services.invoice_service import create_invoice_for_activation

router = APIRouter(
    prefix="/api/platform/organizations",
    tags=["Platform (Owner-only)"],
    dependencies=[Depends(verify_admin_token)],
)

"""
Kein Stripe: Firmenzugänge werden manuell freigeschaltet, nachdem außerhalb
der App eine Zahlung vereinbart wurde (Rechnung/Lastschrift). Diese Routen
sind nur mit dem x-admin-token Header (ADMIN_TOKEN aus .env) erreichbar –
gedacht für den Betreiber, nicht für Kunden. Siehe app/security.py
(organization_has_access) für die Durchsetzung.
"""


@router.get("", response_model=List[OrganizationAdminResponse])
def list_organizations(db: Session = Depends(get_db)):
    return db.query(Organization).order_by(Organization.created_at.desc()).all()


@router.post("/{org_id}/activate", response_model=OrganizationAdminResponse)
def activate_organization(
    org_id: int,
    request: ActivateOrganizationRequest,
    db: Session = Depends(get_db)
):
    """Schaltet eine Firma frei und erstellt dabei automatisch eine Rechnung
    (PDF in R2, Metadaten in Invoice) – active_until=None → unbefristet."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization nicht gefunden.")

    org.is_active = True
    org.plan = request.plan or "active"
    org.active_until = request.active_until
    if request.billing_contact_name:
        org.billing_contact_name = request.billing_contact_name
    if request.billing_email:
        org.billing_email = request.billing_email
    if request.billing_address:
        org.billing_address = request.billing_address
    db.commit()
    db.refresh(org)

    period_start = date.today()
    period_end = request.active_until.date() if request.active_until else period_start + timedelta(days=30)
    create_invoice_for_activation(db, org, period_start, period_end)

    return org


@router.post("/{org_id}/deactivate", response_model=OrganizationAdminResponse)
def deactivate_organization(org_id: int, db: Session = Depends(get_db)):
    """Sperrt eine Firma sofort (z.B. Rechnung nicht bezahlt)."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization nicht gefunden.")

    org.is_active = False
    org.plan = "canceled"
    db.commit()
    db.refresh(org)
    return org


@router.get("/{org_id}/invoices", response_model=List[InvoiceResponse])
def list_invoices(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization nicht gefunden.")
    return (
        db.query(Invoice)
        .filter(Invoice.organization_id == org_id)
        .order_by(Invoice.created_at.desc())
        .all()
    )


@router.get("/{org_id}/invoices/{invoice_id}/pdf")
def download_invoice(org_id: int, invoice_id: int, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.organization_id == org_id
    ).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden.")
    pdf_bytes = storage_service.download_bytes(invoice.pdf_storage_key)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )
