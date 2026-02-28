from sqlalchemy import String, Table, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import SupplierStatus

category_suppliers = Table(
    "category_suppliers",
    Base.metadata,
    mapped_column("supplier_id", ForeignKey("suppliers.id"), primary_key=True),
    mapped_column("category_id", ForeignKey("categories.id"), primary_key=True),
)


class Supplier(Base, TimestampMixin):
    __tablename__ = "suppliers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    status: Mapped[SupplierStatus] = mapped_column(default=SupplierStatus.ACTIVE)

    categories = relationship(
        "Category",
        secondary=category_suppliers,
        back_populates="suppliers",
    )
