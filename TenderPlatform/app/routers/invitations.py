from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import models
from app.dependencies import get_db
from datetime import datetime

router = APIRouter(tags=["Приглашения"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/invite/{token}", response_class=HTMLResponse)
def handle_invite(token: str, request: Request, db: Session = Depends(get_db)):
    invitation = db.query(models.TenderInvitation).filter(
        models.TenderInvitation.token == token,
        models.TenderInvitation.is_used == False,
        models.TenderInvitation.expires_at > datetime.utcnow()
    ).first()
    if not invitation:
        return templates.TemplateResponse("invite_expired.html", {"request": request})

    tender = db.query(models.Tender).filter(models.Tender.id == invitation.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    return templates.TemplateResponse("supplier/invitation.html", {
        "request": request,
        "tender": tender,
        "token": token,
        "email": invitation.supplier_email
    })
