from app.config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email: str, subject: str, body: str):
    """
    Отправка email.
    Если настроек SMTP нет или они неверные, просто выводим в консоль
    (чтобы разработка не стопорилась).
    """
    print(f"--- EMAIL MOCK ---")
    print(f"To: {to_email}")
    print(f"Subject: {subject}")
    print(f"Body: {body}")
    print(f"------------------")

    # Раскомментируй этот блок для реальной отправки, когда будет SMTP
    """
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
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
    """
