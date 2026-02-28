from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.v1.deps import require_permissions
from app.models.round import Round
from app.models.request import Request
from app.models.supplier import Supplier
from app.services.invitation_service import generate_invitation
from app.workers.email_tasks import send_invitation_emails
from app.core.enums import RequestStatus

router = APIRouter(prefix="/requests/{request_id}/rounds", tags=["Rounds"])


@router.post("/")
async def create_round(
    request_id: int,
    payload: RoundCreateSchema,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_permissions(["manage_rounds"])),
):
    request = await db.get(Request, request_id)

    # Определяем номер раунда
    result = await db.execute(
        select(func.max(Round.round_number)).where(Round.request_id == request_id)
    )
    last_round = result.scalar() or 0
    new_number = last_round + 1

    if new_number > request.category.max_rounds:
        raise HTTPException(400, "Max rounds exceeded")

    if new_number > 1 and not request.category.negotiation_allowed:
        raise HTTPException(400, "Negotiation disabled")

    new_round = Round(
        request_id=request_id,
        round_number=new_number,
        type="INITIAL" if new_number == 1 else "NEGOTIATION",
        deadline=payload.deadline,
        comment=payload.comment,
    )

    db.add(new_round)
    await db.commit()
    await db.refresh(new_round)

    # Приглашения только выбранным поставщикам
    invitations = []
    for supplier_id in payload.supplier_ids:
        inv = generate_invitation(new_round.id, supplier_id)
        db.add(inv)
        invitations.append(inv)

    await db.commit()

    send_invitation_emails.delay([i.id for i in invitations])

    return {"round_id": new_round.id}
