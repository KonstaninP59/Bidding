from datetime import datetime
from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import RoundType


class Round(Base, TimestampMixin):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    number: Mapped[int]
    type: Mapped[RoundType]
    deadline: Mapped[datetime]
    comment: Mapped[str | None] = mapped_column(Text)

    request = relationship("Request")
    invitations = relationship("Invitation", cascade="all, delete-orphan")
