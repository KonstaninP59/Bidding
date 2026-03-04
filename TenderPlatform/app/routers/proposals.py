from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app import models, schemas
from app.dependencies import get_db, get_current_active_user
from app.utils import files
from datetime import datetime
import json
import logging

router = APIRouter(prefix="/proposals", tags=["Proposals"])
logger = logging.getLogger(__name__)

@router.post("/", response_model=schemas.ProposalResponse)
async def create_proposal(
    tender_id: int = Form(...),
    round_id: int = Form(...),
    values_json: str = Form(...),
    files_list: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # 1. Проверки прав
    if current_user.role != models.UserRole.SUPPLIER:
        raise HTTPException(status_code=403, detail="Only suppliers can submit proposals")

    # 2. Проверка раунда
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj or round_obj.tender_id != tender_id:
        raise HTTPException(status_code=404, detail="Round not found for this tender")
    
    if round_obj.status != models.RoundStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Round is not active")
    
    if datetime.utcnow() > round_obj.end_time:
        raise HTTPException(status_code=400, detail="Deadline passed")

    # 3. Проверка, что поставщик уже не подавал предложение в этом раунде
    existing = db.query(models.Proposal).filter(
        models.Proposal.round_id == round_id,
        models.Proposal.supplier_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You already have a proposal for this round")

    # 4. Парсим JSON значений
    try:
        values_data = json.loads(values_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format for values")

    # 5. Загружаем критерии тендера для проверки
    criteria = db.query(models.TenderCriterion).filter(
        models.TenderCriterion.tender_id == tender_id
    ).all()
    criterion_ids = {c.id: c for c in criteria}

    # Валидация: все переданные criterion_id должны принадлежать тендеру
    for val in values_data:
        crit_id = val.get('criterion_id')
        if crit_id not in criterion_ids:
            raise HTTPException(status_code=400, detail=f"Criterion {crit_id} not found in this tender")
        # Доп. валидация типа значения (можно добавить)

    # 6. Создаем предложение в рамках одной транзакции
    new_proposal = models.Proposal(
        round_id=round_id,
        supplier_id=current_user.id,
        status=models.ProposalStatus.SENT,
        created_at=datetime.utcnow()
    )
    db.add(new_proposal)
    db.flush()  # чтобы получить id

    # 7. Сохраняем значения критериев
    for val in values_data:
        db_value = models.ProposalValue(
            proposal_id=new_proposal.id,
            criterion_id=val['criterion_id'],
            value_numeric=val.get('value_numeric'),
            value_text=val.get('value_text')
        )
        db.add(db_value)

    # 8. Сохраняем файлы (если есть)
    if files_list:
        for file in files_list:
            if file and file.filename:
                # Проверка размера и типа
                await files.validate_file(file)
                file_path = await files.save_upload_file(file, subfolder="proposals")
                db_file = models.ProposalFile(
                    proposal_id=new_proposal.id,
                    file_path=file_path,
                    file_name=file.filename
                )
                db.add(db_file)

    try:
        db.commit()
        db.refresh(new_proposal)
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error: {e}")
        raise HTTPException(status_code=400, detail="Database integrity error")

    # Загружаем связанные данные для ответа
    result = db.query(models.Proposal).options(
        selectinload(models.Proposal.values),
        selectinload(models.Proposal.files)
    ).filter(models.Proposal.id == new_proposal.id).first()

    return result

@router.get("/my", response_model=List[schemas.ProposalResponse])
def read_my_proposals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    proposals = db.query(models.Proposal).filter(
        models.Proposal.supplier_id == current_user.id
    ).options(
        selectinload(models.Proposal.values),
        selectinload(models.Proposal.files)
    ).all()
    return proposals
