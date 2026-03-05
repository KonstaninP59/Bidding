from sqlalchemy.orm import Session
from app import models
import json


def log_action(db: Session, user_id: int, action: str, target_object: str = None, details: dict = None):
    log = models.AuditLog(
        user_id=user_id,
        action=action,
        target_object=target_object,
        details=json.dumps(details, ensure_ascii=False) if details else None
    )
    db.add(log)
    db.commit()  # лучше коммитить отдельно, но осторожно


def log_email(user_id: int, recipient: str, subject: str, body_preview: str, status: str, error: str = None):
    # используется в email.py, не требует сессии на момент вызова – передадим позже
    # Здесь просто заглушка, реальное логирование делаем в email.py с db
    pass
