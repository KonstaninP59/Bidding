from fastapi import Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.invitation import Invitation
from app.models.round import Round
from app.core.security import pwd_context
from datetime import datetime


async def get_invitation_from_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Invitation))
    invitations = result.scalars().all()

    for invitation in invitations:
        if pwd_context.verify(token, invitation.token_hash):
            round_obj = await db.get(Round, invitation.round_id)

            if datetime.utcnow() > round_obj.deadline:
                raise HTTPException(403, "Deadline passed")

            if round_obj.closed_at:
                raise HTTPException(403, "Round closed")

            return invitation

    raise HTTPException(404, "Invalid token")
