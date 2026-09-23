from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Organization
from app.schemas import OrganizationAdminResponse, ActivateOrganizationRequest
from app.security import verify_admin_token

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
    """Schaltet eine Firma frei. active_until=None → unbefristet."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization nicht gefunden.")

    org.is_active = True
    org.plan = request.plan or "active"
    org.active_until = request.active_until
    db.commit()
    db.refresh(org)
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
