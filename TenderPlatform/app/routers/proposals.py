from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from app import models, schemas
from app.dependencies import get_db, get_current_active_user
from app.utils import files, scoring, audit
from datetime import datetime
import json
import logging

router = APIRouter(prefix="/api/proposals", tags=["Предложения"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=schemas.ProposalResponse)
async def create_proposal(
    tender_id: int = Form(...),
    round_id: int = Form(...),
    values_json: str = Form(...),
    files_list: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_active_user)  # может быть None для неавторизованных
):
    # Если пользователь не авторизован, проверяем наличие токена в query или form
    # Для простоты считаем, что неавторизованный может подать, но потом ему предложат создать кабинет
    # В реальности нужно проверять приглашение по токену (опустим для краткости)

    # Проверка раунда
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj or round_obj.tender_id != tender_id:
        raise HTTPException(status_code=404, detail="Раунд не найден")
    if round_obj.status != models.RoundStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Раунд не активен")
    if datetime.utcnow() > round_obj.end_time:
        raise HTTPException(status_code=400, detail="Дедлайн истёк")

    # Если пользователь не авторизован, создаём временного? Нет, просто разрешаем, но supplier_id = None?
    # По логике гибрида C: поставщик переходит по ссылке, может подать без регистрации.
    # Для этого нужно разрешить proposal без supplier_id, но потом связать.
    # Упростим: требуем авторизацию, но дадим возможность создать кабинет после отправки.
    # В реальном проекте нужна более сложная логика.

    # Проверка, что поставщик уже не подавал предложение в этом раунде
    if current_user:
        existing = db.query(models.Proposal).filter(
            models.Proposal.round_id == round_id,
            models.Proposal.supplier_id == current_user.id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Вы уже подали предложение в этом раунде")
        supplier_id = current_user.id
    else:
        # Неавторизованный: создаём запись с supplier_id = None? Но тогда потом нужно будет привязать.
        # Для простоты пока запретим неавторизованным. В реальном проекте нужно через токен приглашения.
        raise HTTPException(status_code=401, detail="Необходимо авторизоваться")

    # Парсим JSON
    try:
        values_data = json.loads(values_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Неверный формат JSON")

    # Загружаем критерии тендера
    criteria = db.query(models.TenderCriterion).filter(
        models.TenderCriterion.tender_id == tender_id
    ).all()
    criterion_ids = {c.id: c for c in criteria}

    for val in values_data:
        crit_id = val.get('criterion_id')
        if crit_id not in criterion_ids:
            raise HTTPException(status_code=400, detail=f"Критерий {crit_id} не найден в этом тендере")

    # Создаём предложение
    new_proposal = models.Proposal(
        round_id=round_id,
        supplier_id=supplier_id,
        status=models.ProposalStatus.SENT,
        created_at=datetime.utcnow()
    )
    db.add(new_proposal)
    db.flush()

    # Значения критериев
    for val in values_data:
        db_value = models.ProposalValue(
            proposal_id=new_proposal.id,
            criterion_id=val['criterion_id'],
            value_numeric=val.get('value_numeric'),
            value_text=val.get('value_text')
        )
        db.add(db_value)

    # Файлы
    if files_list:
        for file in files_list:
            if file and file.filename:
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
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Integrity error: {e}")
        raise HTTPException(status_code=400, detail="Ошибка базы данных")

    audit.log_action(db, supplier_id, "CREATE_PROPOSAL", f"Proposal {new_proposal.id}", {"round_id": round_id})

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
        selectinload(models.Proposal.files),
        selectinload(models.Proposal.round).selectinload(models.TenderRound.tender)
    ).all()
    return proposals


@router.get("/round/{round_id}", response_model=List[schemas.ProposalResponse])
def get_round_proposals(
    round_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Проверка прав (заказчик или админ)
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Раунд не найден")
    tender = db.query(models.Tender).filter(models.Tender.id == round_obj.tender_id).first()
    if tender.owner_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Недостаточно прав")
    proposals = db.query(models.Proposal).filter(
        models.Proposal.round_id == round_id
    ).options(
        selectinload(models.Proposal.values),
        selectinload(models.Proposal.files),
        selectinload(models.Proposal.supplier)
    ).all()
    return proposals
