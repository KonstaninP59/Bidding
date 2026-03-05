import secrets
from datetime import datetime, timedelta
from app.config import settings


def generate_invite_token() -> str:
    return secrets.token_urlsafe(32)


def get_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=settings.INVITE_TOKEN_EXPIRE_HOURS)
