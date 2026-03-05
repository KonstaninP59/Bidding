from pydantic_settings import BaseSettings
from typing import Optional, Set

class Settings(BaseSettings):
    # База данных
    DATABASE_URL: str = "sqlite:///./tender.db"

    # Безопасность
    SECRET_KEY: str = "change_this_secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Почта
    MAIL_USERNAME: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_SERVER: str = "smtp.gmail.com"

    # Загрузка файлов
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS: Set[str] = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".png"}

    # Приглашения
    INVITE_TOKEN_EXPIRE_HOURS: int = 72

    class Config:
        env_file = ".env"

settings = Settings()
