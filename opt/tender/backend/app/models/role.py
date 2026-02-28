from sqlalchemy import String, Table, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    mapped_column("role_id", ForeignKey("roles.id"), primary_key=True),
    mapped_column("permission_id", ForeignKey("permissions.id"), primary_key=True),
)


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)

    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
