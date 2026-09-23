"""
Dünner Wrapper um die Resend-REST-API für Transaktions-Mails (kein SDK, ein
einzelner Endpoint reicht). Ohne RESEND_API_KEY/RESEND_FROM_EMAIL wird die
Mail nur geloggt statt versendet, damit lokale Entwicklung ohne eigenes
Resend-Konto funktioniert – gleiches Muster wie bei LeadSpeak AI.
"""
import logging
import os

import httpx

logger = logging.getLogger("onboardguide.email")

RESEND_API_URL = "https://api.resend.com/emails"


def send_email(to: str, subject: str, html: str, reply_to: str | None = None) -> None:
    api_key = os.getenv("RESEND_API_KEY")
    from_email = os.getenv("RESEND_FROM_EMAIL")

    if not api_key or not from_email:
        logger.info("[email:mock] %s -> %s", subject, to)
        return

    payload = {"from": from_email, "to": to, "subject": subject, "html": html}
    if reply_to:
        payload["reply_to"] = reply_to

    response = httpx.post(
        RESEND_API_URL,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
