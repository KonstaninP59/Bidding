from app.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)

def send_email(to_email: str, subject: str, body: str):
    """
    Отправка email. Если SMTP не настроен, логирует.
    """
    if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
        logger.info(f"Email not sent (no SMTP config): to={to_email}, subject={subject}")
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
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
