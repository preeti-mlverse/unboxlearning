"""Transactional email. With SMTP configured, messages are sent; without it (local development) they are written
to storage/outbox/*.txt and logged, so verification and reset links can still be clicked."""
import logging
import smtplib
import ssl
from email.message import EmailMessage

from ..config import get_settings
from ..db import utcnow

log = logging.getLogger("unboxed.mail")


def send(to: str, subject: str, text: str) -> None:
    s = get_settings()
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = s.smtp_from, to, subject
    msg.set_content(text)
    if not s.smtp_host:
        outbox = s.storage_dir / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        name = f"{utcnow().strftime('%Y%m%d-%H%M%S-%f')}-{subject.split()[0].lower()}.txt"
        (outbox / name).write_text(f"To: {to}\nSubject: {subject}\n\n{text}", encoding="utf-8")
        log.info("email written to outbox (no SMTP configured): %s -> %s", subject, outbox / name)
        return
    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(msg)
    except Exception:  # an email problem must never break sign-up; it's logged and the person can resend
        log.exception("could not send email: %s", subject)


def verification_email(to: str, name: str, token: str, code: str) -> None:
    link = f"{get_settings().app_url}/verify-email?token={token}"
    send(to, f"{code} is your UnboxEd code", f"Hi {name},\n\nYour UnboxEd confirmation code is:\n\n    {code}\n\n"
         f"Type it into UnboxEd to confirm your email. It works for 30 minutes.\n\nOr open this link instead "
         f"(it works for 48 hours):\n{link}\n\nIf you didn't sign up, you can ignore this email.\n\n— UnboxEd")


def reset_email(to: str, name: str, token: str) -> None:
    link = f"{get_settings().app_url}/reset-password?token={token}"
    send(to, "Reset your UnboxEd password", f"Hi {name},\n\nSomeone (hopefully you) asked to reset your UnboxEd password. "
         f"Choose a new one here:\n\n{link}\n\nThis link works for 1 hour and only once. If you didn't ask, ignore this "
         "email and your password stays the same.\n\n— UnboxEd")
