from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models.base import TimestampMixin


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"))
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))

    file_path: Mapped[str] = mapped_column(String(500))
    snapshot_data: Mapped[dict] = mapped_column(JSON)
