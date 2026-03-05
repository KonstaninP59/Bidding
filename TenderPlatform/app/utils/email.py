from app.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from app.utils.audit import log_email

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str, user_id: int = None):
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.info(f"[EMAIL] to={to_email}, subject={subject}\n{body}")
        log_email(user_id, to_email, subject, body[:100], "simulated")
        return

    try:
        message = MIMEMultipart()
        message["From"] = settings.MAIL_FROM
        message["To"] = to_email
        message["Subject"] = subject
        message.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.MAIL_SERVER, settings.MAIL_PORT) as server:
            server.starttls()
            server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            server.send_message(message)
        logger.info(f"Email sent to {to_email}")
        log_email(user_id, to_email, subject, body[:100], "sent")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        log_email(user_id, to_email, subject, body[:100], "failed", str(e))
        