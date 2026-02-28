from sqlalchemy import ForeignKey, Numeric, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin


class Offer(Base, TimestampMixin):
    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(primary_key=True)
    invitation_id: Mapped[int] = mapped_column(ForeignKey("invitations.id"))

    payment_terms: Mapped[str | None]
    comment: Mapped[str | None] = mapped_column(Text)

    items = relationship("OfferItem", cascade="all, delete-orphan")


class OfferItem(Base, TimestampMixin):
    __tablename__ = "offer_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    offer_id: Mapped[int] = mapped_column(ForeignKey("offers.id"))
    request_item_id: Mapped[int] = mapped_column(ForeignKey("request_items.id"))

    unit_price: Mapped[float]
    delivery_time: Mapped[str | None]
    not_available: Mapped[bool] = mapped_column(Boolean, default=False)
