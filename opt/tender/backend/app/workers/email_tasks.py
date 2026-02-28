from app.workers.celery_app import celery
from app.services.email import send_email
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import async_session_factory
from app.models.invitation import Invitation
from app.models.supplier import Supplier
import os


@celery.task(bind=True, max_retries=3)
def send_invitation_emails(self, invitation_ids: list[int]):
    import asyncio

    async def _send():
        async with async_session_factory() as db:
            result = await db.execute(
                select(Invitation).where(Invitation.id.in_(invitation_ids))
            )
            invitations = result.scalars().all()

            for invitation in invitations:
                supplier = await db.get(Supplier, invitation.supplier_id)

                public_link = (
                    f"{os.getenv('FRONTEND_URL')}/public/offer/"
                    f"{invitation.token_plain}"  # передаётся временно
                )

                send_email(
                    supplier.email,
                    "Приглашение в раунд",
                    f"Ссылка: {public_link}",
                )

    asyncio.run(_send())
