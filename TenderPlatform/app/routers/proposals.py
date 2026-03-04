from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app import models, schemas
from app.dependencies import get_db, get_current_active_user
from app.utils import files
from datetime import datetime
import json

router = APIRouter(prefix="/proposals", tags=["Proposals"])

@router.post("/", response_model=schemas.ProposalResponse)
async def create_proposal(
    tender_id: int = Form(...),
    round_id: int = Form(...),
    values_json: str = Form(...), # Получаем значения критериев как JSON строку
    files_list: List[UploadFile] = File(None), # Список файлов
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Подача предложения поставщиком.
    Принимает данные формы (multipart/form-data), так как есть загрузка файлов.
    """
    # 1. Проверки
    if current_user.role != models.UserRole.SUPPLIER:
        raise HTTPException(status_code=403, detail="Only suppliers can submit proposals")

    # Проверяем, существует ли раунд и активен ли он
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Round not found")
    
    if datetime.utcnow() > round_obj.end_time:
        raise HTTPException(status_code=400, detail="Deadline passed")

    # 2. Создаем объект Предложения
    new_proposal = models.Proposal(
        round_id=round_id,
        supplier_id=current_user.id,
        status=models.ProposalStatus.SENT,
        created_at=datetime.utcnow()
    )
    db.add(new_proposal)
    db.commit()
    db.refresh(new_proposal)

    # 3. Сохраняем значения критериев (Цены, Сроки и т.д.)
    try:
        values_data = json.loads(values_json) # Парсим JSON из строки
        for val in values_data:
            db_value = models.ProposalValue(
                proposal_id=new_proposal.id,
                criterion_id=val['criterion_id'],
                value_numeric=val.get('value_numeric'),
                value_text=val.get('value_text')
            )
            db.add(db_value)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for values")

    # 4. Сохраняем файлы (если есть)
    if files_list:
        for file in files_list:
            if file.filename: # Если файл действительно выбран
                file_path = files.save_upload_file(file, subfolder="proposals")
                db_file = models.ProposalFile(
                    proposal_id=new_proposal.id,
                    file_path=file_path,
                    file_name=file.filename
                )
                db.add(db_file)

    db.commit()
    db.refresh(new_proposal)
    return new_proposal

@router.get("/my", response_model=List[schemas.ProposalResponse])
def read_my_proposals(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_active_user)):
    """Посмотреть свои предложения"""
    proposals = db.query(models.Proposal).filter(models.Proposal.supplier_id == current_user.id).all()
    return proposals
