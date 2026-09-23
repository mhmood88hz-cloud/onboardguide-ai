import os

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import ContactRequest
from app.security import get_current_user, load_current_user
from app.services.email_service import send_email
from app.services.rate_limit import limiter

router = APIRouter(prefix="/api/contact", tags=["Contact"])

REASON_LABELS = {"subscribe": "Abo-Interesse", "general": "Allgemeine Anfrage"}


@router.post("", status_code=202)
@limiter.limit("3/15minute")
def send_contact_request(
    request:      Request,
    body:         ContactRequest,
    db:           Session = Depends(get_db),
    user_id:      int     = Depends(get_current_user),
):
    """
    Kein Stripe/Checkout (bewusste Entscheidung – siehe README "Billing"):
    statt eines echten Bezahlvorgangs geht eine formatierte Anfrage per
    E-Mail an den Anbieter (OWNER_EMAIL), der Interessent:innen manuell
    kontaktiert und die Firma danach über /api/platform/organizations
    freischaltet.
    """
    current_user = load_current_user(user_id, db)
    owner_email  = os.getenv("OWNER_EMAIL", "owner@example.com")
    member_count = db.query(User).filter(User.organization_id == current_user.organization_id).count()
    reason_label = REASON_LABELS[body.reason]

    send_email(
        to=owner_email,
        subject=f"OnboardGuide AI — {reason_label} von {current_user.email} (Firma: {current_user.organization.name})",
        reply_to=current_user.email,
        html=f"""
            <p><strong>Grund:</strong> {reason_label}</p>
            <p><strong>Von:</strong> {current_user.username} ({current_user.user_role}) &lt;{current_user.email}&gt;</p>
            <p><strong>Firma:</strong> {current_user.organization.name} — {member_count} Mitglied(er)</p>
            {f"<p><strong>Nachricht:</strong><br/>{body.message.replace(chr(10), '<br/>')}</p>" if body.message else ""}
        """.strip(),
    )

    return {"status": "sent"}
