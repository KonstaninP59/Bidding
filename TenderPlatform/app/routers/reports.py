from fastapi import APIRouter, Depends, HTTPException
# from fastapi.responses import PlainTextResponse, Response
# from sqlalchemy.orm import Session, selectinload
# from app import models, schemas
# from app.dependencies import get_db, get_current_customer
# from app.utils import audit
# from weasyprint import HTML
# from jinja2 import Template
# import os

router = APIRouter(prefix="/api/reports", tags=["Отчёты"])


# @router.get("/tender/{tender_id}/pdf")
# def generate_pdf_report(
#     tender_id: int,
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_customer)
# ):
#     return PlainTextResponse("Генерация PDF временно недоступна. Установите GTK для работы WeasyPrint.", status_code=501)
