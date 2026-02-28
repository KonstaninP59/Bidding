from sqlalchemy import ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import AuditAction


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[AuditAction]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    details: Mapped[dict] = mapped_column(JSON)
