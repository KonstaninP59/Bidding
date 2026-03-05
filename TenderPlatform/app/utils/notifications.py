from app.utils.email import send_email
from app.config import settings
from typing import Optional
from jinja2 import Template
import os


def render_template(template_name: str, **kwargs) -> str:
    template_path = os.path.join("app", "templates", "emails", template_name)
    with open(template_path, encoding="utf-8") as f:
        template = Template(f.read())
    return template.render(**kwargs)


def send_invitation(email: str, tender_title: str, tender_id: int, token: str, deadline, contact):
    link = f"http://localhost:8000/invite/{token}"  # в проде заменить на реальный домен
    subject = f"Приглашение к участию в тендере №{tender_id}"
    body = render_template("invitation.html",
                           tender_title=tender_title,
                           tender_id=tender_id,
                           deadline=deadline.strftime("%d.%m.%Y %H:%M"),
                           link=link,
                           contact=contact)
    send_email(email, subject, body)


def send_round_start(email: str, tender_title: str, round_number: int, deadline):
    subject = f"Старт нового раунда тендера {tender_title}"
    body = render_template("round_start.html",
                           tender_title=tender_title,
                           round_number=round_number,
                           deadline=deadline.strftime("%d.%m.%Y %H:%M"))
    send_email(email, subject, body)


def send_deadline_changed(email: str, tender_title: str, new_deadline):
    subject = f"Изменение дедлайна тендера {tender_title}"
    body = render_template("deadline_changed.html",
                           tender_title=tender_title,
                           new_deadline=new_deadline.strftime("%d.%m.%Y %H:%M"))
    send_email(email, subject, body)


def send_result(email: str, tender_title: str, won: bool, rank: int = None):
    subject = f"Результаты тендера {tender_title}"
    body = render_template("result.html",
                           tender_title=tender_title,
                           won=won,
                           rank=rank)
    send_email(email, subject, body)


def send_accreditation_result(email: str, company_name: str, status: str, comment: str = None):
    subject = "Результат проверки аккредитации"
    body = render_template("accreditation_result.html",
                           company_name=company_name,
                           status=status,
                           comment=comment)
    send_email(email, subject, body)
