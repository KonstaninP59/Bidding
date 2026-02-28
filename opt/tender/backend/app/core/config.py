import os
from pydantic import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Tender Platform"
    API_V1_STR: str = "/api/v1"

    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "tender")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "db")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", 5432))

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    SECRET_KEY: str = os.getenv("SECRET_KEY", "CHANGE_ME")

    class Config:
        env_file = ".env"


settings = Settings()
