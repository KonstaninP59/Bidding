from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin
from app.core.enums import InvitationStatus


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"))

    token_hash: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[InvitationStatus] = mapped_column(default=InvitationStatus.SENT)

    round = relationship("Round")
    supplier = relationship("Supplier")
