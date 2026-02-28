from sqlalchemy import String, Text, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import RequestStatus


class Request(Base, TimestampMixin):
    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    subject: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    status: Mapped[RequestStatus] = mapped_column(default=RequestStatus.DRAFT)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    category = relationship("Category")

    items = relationship("RequestItem", cascade="all, delete-orphan")


class RequestItem(Base, TimestampMixin):
    __tablename__ = "request_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float]
    unit: Mapped[str] = mapped_column(String(50))
