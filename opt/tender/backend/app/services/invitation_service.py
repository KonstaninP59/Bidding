import secrets
from app.core.security import pwd_context
from app.models.invitation import Invitation
from app.core.enums import InvitationStatus


def generate_invitation(round_id: int, supplier_id: int):
    token = secrets.token_urlsafe(32)
    token_hash = pwd_context.hash(token)

    invitation = Invitation(
        round_id=round_id,
        supplier_id=supplier_id,
        token_hash=token_hash,
        status=InvitationStatus.SENT,
    )

    # временно сохраняем plain в объект (не в БД)
    invitation.token_plain = token
    return invitation
