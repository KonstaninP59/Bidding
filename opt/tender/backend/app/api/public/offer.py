from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from datetime import datetime
import os
import uuid

from app.core.database import get_db
from app.api.public.deps import get_invitation_from_token
from app.models.offer import Offer, OfferItem
from app.models.request import RequestItem
from app.models.invitation import Invitation
from app.models.attachment import Attachment
from app.core.enums import InvitationStatus
from app.core.rate_limiter import check_rate_limit
from app.workers.email_tasks import send_confirmation_email

router = APIRouter(prefix="/public/offer", tags=["Public Offer"])
UPLOAD_DIR = "media/offers"
MAX_FILE_SIZE_MB = 20
ALLOWED_TYPES = ["application/pdf", "application/vnd.openxmlformats-officedocument"]

@router.get("/{token}")
async def get_offer_form(
    token: str,
    invitation: Invitation = Depends(get_invitation_from_token),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(f"public:{token}")

    round_obj = invitation.round
    request = round_obj.request

    # позиции
    items = request.items

    # previous offer (если negotiation)
    previous_offer_data = None
    if round_obj.number > 1:
        prev_round_number = round_obj.number - 1
        result = await db.execute(
            select(Offer)
            .join(Invitation)
            .join(Invitation.round)
            .where(
                Invitation.supplier_id == invitation.supplier_id,
                Invitation.round.has(number=prev_round_number),
            )
        )
        prev_offer = result.scalar_one_or_none()

        if prev_offer:
            previous_offer_data = {
                "items": [
                    {
                        "request_item_id": i.request_item_id,
                        "unit_price": i.unit_price,
                        "delivery_time": i.delivery_time,
                    }
                    for i in prev_offer.items
                ],
                "total_amount": prev_offer.total_amount,
            }

    return {
        "request_number": request.request_number,
        "subject": request.subject,
        "deadline": round_obj.deadline,
        "items": items,
        "previous_offer": previous_offer_data,
    }


@router.post("/{token}")
async def submit_offer(
    token: str,
    payment_terms: str = Form(None),
    comment: str = Form(None),
    files: List[UploadFile] = File([]),
    invitation: Invitation = Depends(get_invitation_from_token),
    db: AsyncSession = Depends(get_db),
):
    await check_rate_limit(f"public_submit:{token}")

    offer = Offer(
        invitation_id=invitation.id,
        payment_terms=payment_terms,
        comment=comment,
    )

    db.add(offer)
    await db.flush()

    # обязательное обновление всех позиций (FR-22)
    request_items = invitation.round.request.items

    for item in request_items:
        form_price = float(
            (await invitation._request.form()).get(f"price_{item.id}")
        )

        db.add(
            OfferItem(
                offer_id=offer.id,
                request_item_id=item.id,
                unit_price=form_price,
                line_total=form_price * float(item.quantity),
            )
        )

    # вложения
    for file in files:
        if file.content_type not in ALLOWED_TYPES:
            continue

        contents = await file.read()
        if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
            continue

        filename = f"{uuid.uuid4()}_{file.filename}"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as f:
            f.write(contents)

        db.add(
            Attachment(
                file_name=file.filename,
                file_path=path,
                content_type=file.content_type,
                offer_id=offer.id,
            )
        )

    invitation.status = InvitationStatus.RESPONDED
    invitation.responded_at = datetime.utcnow()

    await db.commit()

    send_confirmation_email.delay(invitation.id)

    return {"status": "submitted"}


@celery.task
def send_confirmation_email(invitation_id: int):
    ...
