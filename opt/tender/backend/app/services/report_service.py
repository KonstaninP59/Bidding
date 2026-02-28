from sqlalchemy import select
from app.models.request import Request
from app.models.offer import Offer
from app.models.invitation import Invitation
from app.models.round import Round
import os
import uuid
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from openpyxl import Workbook
import matplotlib.pyplot as plt


async def build_snapshot(db, request_id, round_id):
    request = await db.get(Request, request_id)

    result = await db.execute(
        select(Offer)
        .join(Invitation)
        .where(Invitation.round_id == round_id)
    )

    offers = result.scalars().unique().all()

    return {
        "request": {
            "number": request.request_number,
            "subject": request.subject,
        },
        "offers": [
            {
                "supplier_id": o.invitation.supplier_id,
                "total": sum(i.line_total for i in o.items),
            }
            for o in offers
        ]
    }
