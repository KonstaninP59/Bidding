from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text)

    suppliers = relationship(
        "Supplier",
        secondary="category_suppliers",
        back_populates="categories",
    )


negotiation_allowed: Mapped[bool] = mapped_column(default=True)
forbid_price_increase: Mapped[bool] = mapped_column(default=True)
require_full_update: Mapped[bool] = mapped_column(default=True)
max_rounds: Mapped[int] = mapped_column(default=2)
