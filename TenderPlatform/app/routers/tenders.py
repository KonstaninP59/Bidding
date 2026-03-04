from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from app import models, schemas
from app.dependencies import get_db, get_current_active_user
from datetime import datetime

router = APIRouter(prefix="/tenders", tags=["Tenders"])

@router.post("/", response_model=schemas.TenderResponse)
def create_tender(
    tender_data: schemas.TenderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    # Проверка прав
    if current_user.role not in [models.UserRole.CUSTOMER, models.UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Only customers can create tenders")

    # Доп. проверка суммы весов (дублируем валидацию схемы для надежности)
    total_weight = sum(c.weight for c in tender_data.criteria)
    if abs(total_weight - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail="Sum of criterion weights must be 100%")

    # 1. Создаем тендер
    new_tender = models.Tender(
        title=tender_data.title,
        description=tender_data.description,
        currency=tender_data.currency,
        has_lots=tender_data.has_lots,
        is_vendor_rank_visible=tender_data.is_vendor_rank_visible,
        owner_id=current_user.id,
        status=models.TenderStatus.PUBLISHED  # сразу публикуем
    )
    db.add(new_tender)
    db.flush()

    # 2. Добавляем позиции
    for item in tender_data.items:
        db_item = models.TenderItem(
            tender_id=new_tender.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            requirements=item.requirements
        )
        db.add(db_item)

    # 3. Добавляем критерии
    for crit in tender_data.criteria:
        db_crit = models.TenderCriterion(
            tender_id=new_tender.id,
            name=crit.name,
            weight=crit.weight,
            criterion_type=crit.criterion_type,
            is_mandatory=crit.is_mandatory
        )
        db.add(db_crit)
    
    # 4. Создаем первый раунд
    first_round = models.TenderRound(
        tender_id=new_tender.id,
        round_number=1,
        start_time=datetime.utcnow(),
        end_time=tender_data.first_round_deadline,
        status=models.RoundStatus.ACTIVE
    )
    db.add(first_round)
    
    db.commit()
    
    # Возвращаем с загрузкой связанных данных
    result = db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == new_tender.id).first()
    
    return result

@router.get("/", response_model=List[schemas.TenderResponse])
def read_tenders(
    skip: int = 0,
    limit: int = 100,
    status: models.TenderStatus = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Tender)
    if status:
        query = query.filter(models.Tender.status == status)
    else:
        # По умолчанию только опубликованные
        query = query.filter(models.Tender.status == models.TenderStatus.PUBLISHED)
    
    tenders = query.options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).offset(skip).limit(limit).all()
    return tenders

@router.get("/{tender_id}", response_model=schemas.TenderResponse)
def read_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == tender_id).first()
    
    if tender is None:
        raise HTTPException(status_code=404, detail="Tender not found")
    return tender
