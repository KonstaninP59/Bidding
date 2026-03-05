from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app import models, schemas
from app.dependencies import get_db, get_current_customer
from datetime import datetime
from app.utils import notifications, audit

router = APIRouter(prefix="/api/rounds", tags=["Раунды"])


@router.post("/{tender_id}/next", response_model=schemas.TenderRoundResponse)
def create_next_round(
    tender_id: int,
    round_data: schemas.TenderRoundCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    tender = db.query(models.Tender).filter(models.Tender.id == tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")

    # Проверяем, что предыдущий раунд завершён
    last_round = db.query(models.TenderRound).filter(
        models.TenderRound.tender_id == tender_id
    ).order_by(models.TenderRound.round_number.desc()).first()
    if not last_round or last_round.status != models.RoundStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Предыдущий раунд ещё не завершён")

    # Новый номер
    new_number = last_round.round_number + 1

    # Создаём раунд
    new_round = models.TenderRound(
        tender_id=tender_id,
        round_number=new_number,
        end_time=round_data.end_time,
        status=models.RoundStatus.PLANNED
    )
    db.add(new_round)
    db.flush()

    # Добавляем допущенных поставщиков
    if round_data.allowed_supplier_ids:
        for supplier_id in round_data.allowed_supplier_ids:
            allowed = models.RoundAllowedSupplier(
                round_id=new_round.id,
                supplier_id=supplier_id
            )
            db.add(allowed)

    db.commit()
    db.refresh(new_round)

    # Отправляем уведомления допущенным
    for supplier_id in (round_data.allowed_supplier_ids or []):
        supplier = db.query(models.User).filter(models.User.id == supplier_id).first()
        if supplier:
            notifications.send_round_start(supplier.email, tender.title, new_number, round_data.end_time)

    audit.log_action(db, current_user.id, "CREATE_ROUND", f"Tender {tender_id}", {"round": new_number})

    return new_round


@router.post("/{round_id}/activate")
def activate_round(
    round_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj:
        raise HTTPException(status_code=404, detail="Раунд не найден")
    tender = db.query(models.Tender).filter(models.Tender.id == round_obj.tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=403, detail="Нет доступа")

    if round_obj.status != models.RoundStatus.PLANNED:
        raise HTTPException(status_code=400, detail="Раунд нельзя активировать")
    round_obj.status = models.RoundStatus.ACTIVE
    round_obj.start_time = datetime.utcnow()
    db.commit()
    return {"message": "Раунд активирован"}
