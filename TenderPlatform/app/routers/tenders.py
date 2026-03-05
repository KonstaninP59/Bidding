from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload
from typing import List
from app import models, schemas
from app.dependencies import get_db, get_current_customer
from app.utils import tokens, notifications, audit
from datetime import datetime

router = APIRouter(prefix="/api/tenders", tags=["Тендеры"])


@router.post("/", response_model=schemas.TenderResponse)
def create_tender(
    tender_data: schemas.TenderCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    # Проверка суммы весов
    total_weight = sum(c.weight for c in tender_data.criteria)
    if abs(total_weight - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail="Сумма весов критериев должна быть 100%")

    # Создаём тендер в статусе черновик
    new_tender = models.Tender(
        title=tender_data.title,
        description=tender_data.description,
        currency=tender_data.currency,
        has_lots=tender_data.has_lots,
        is_vendor_rank_visible=tender_data.is_vendor_rank_visible,
        owner_id=current_user.id,
        status=models.TenderStatus.DRAFT
    )
    db.add(new_tender)
    db.flush()

    # Позиции
    for item in tender_data.items:
        db_item = models.TenderItem(
            tender_id=new_tender.id,
            name=item.name,
            quantity=item.quantity,
            unit=item.unit,
            requirements=item.requirements
        )
        db.add(db_item)

    # Критерии
    for crit in tender_data.criteria:
        db_crit = models.TenderCriterion(
            tender_id=new_tender.id,
            name=crit.name,
            weight=crit.weight,
            criterion_type=crit.criterion_type,
            is_mandatory=crit.is_mandatory,
            scale=crit.scale
        )
        db.add(db_crit)

    # Раунд 1 (пока не активен, будет активирован при публикации)
    first_round = models.TenderRound(
        tender_id=new_tender.id,
        round_number=1,
        end_time=tender_data.first_round_deadline,
        status=models.RoundStatus.PLANNED
    )
    db.add(first_round)

    db.commit()
    audit.log_action(db, current_user.id, "CREATE_TENDER", f"Tender {new_tender.id}", {"title": new_tender.title})
    return db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == new_tender.id).first()


@router.post("/{tender_id}/publish", response_model=schemas.TenderResponse)
def publish_tender(
    tender_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    if tender.status != models.TenderStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Тендер уже опубликован или завершён")

    # Проверяем наличие критериев
    criteria_count = db.query(models.TenderCriterion).filter(models.TenderCriterion.tender_id == tender_id).count()
    if criteria_count == 0:
        raise HTTPException(status_code=400, detail="Необходимо настроить критерии оценки")

    # Активируем первый раунд
    first_round = db.query(models.TenderRound).filter(
        models.TenderRound.tender_id == tender_id,
        models.TenderRound.round_number == 1
    ).first()
    if first_round:
        first_round.status = models.RoundStatus.ACTIVE
        first_round.start_time = datetime.utcnow()

    tender.status = models.TenderStatus.PUBLISHED
    tender.published_at = datetime.utcnow()
    db.commit()
    db.refresh(tender)

    audit.log_action(db, current_user.id, "PUBLISH_TENDER", f"Tender {tender_id}")

    # TODO: отправка приглашений поставщикам (будет отдельный эндпоинт)
    return tender


@router.post("/{tender_id}/invite")
def invite_suppliers(
    tender_id: int,
    emails: List[str],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")

    contact = f"{current_user.full_name}, {current_user.email}"
    for email in emails:
        # Проверяем, не приглашён ли уже
        existing = db.query(models.TenderInvitation).filter(
            models.TenderInvitation.tender_id == tender_id,
            models.TenderInvitation.supplier_email == email
        ).first()
        if existing:
            continue
        token = tokens.generate_invite_token()
        expires = tokens.get_token_expiry()
        invitation = models.TenderInvitation(
            tender_id=tender_id,
            supplier_email=email,
            token=token,
            expires_at=expires
        )
        db.add(invitation)
        # Отправляем email
        notifications.send_invitation(email, tender.title, tender_id, token, tender.rounds[0].end_time, contact)
    db.commit()
    audit.log_action(db, current_user.id, "INVITE_SUPPLIERS", f"Tender {tender_id}", {"emails": emails})
    return {"message": "Приглашения отправлены"}


@router.get("/{tender_id}", response_model=schemas.TenderResponse)
def get_tender(tender_id: int, db: Session = Depends(get_db)):
    tender = db.query(models.Tender).options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).filter(models.Tender.id == tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    return tender


@router.get("/", response_model=List[schemas.TenderResponse])
def list_tenders(
    skip: int = 0,
    limit: int = 100,
    status: models.TenderStatus = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Tender)
    if status:
        query = query.filter(models.Tender.status == status)
    else:
        query = query.filter(models.Tender.status == models.TenderStatus.PUBLISHED)
    tenders = query.options(
        selectinload(models.Tender.items),
        selectinload(models.Tender.criteria),
        selectinload(models.Tender.rounds)
    ).offset(skip).limit(limit).all()
    return tenders