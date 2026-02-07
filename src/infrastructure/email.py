# src/infrastructure/email.py
import os
from typing import Optional
import aiosmtplib
from email.message import EmailMessage
import structlog

logger = structlog.get_logger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "no-reply@example.com")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

async def send_email(
    to_email: str,
    subject: str,
    plain_text: str,
    html: Optional[str] = None
) -> None:
    """
    Send an email asynchronously using SMTP (aiosmtplib).
    Raises exception on failure.
    """
    if ENVIRONMENT == "development" and (not SMTP_HOST or not SMTP_USER):
        # در حالت توسعه اگر SMTP کانفیگ نشده، فقط لاگ می‌کنیم و برمی‌گردیم
        logger.info("email_send_stub_dev", to=to_email, subject=subject)
        return

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(plain_text)
    if html:
        msg.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER or None,
            password=SMTP_PASSWORD or None,
            start_tls=True if SMTP_PORT in (587, 25) else False,
        )
        logger.info("email_sent", to=to_email, subject=subject)
    except Exception as e:
        logger.exception("email_send_failed", to=to_email, subject=subject, error=str(e))
        raise
