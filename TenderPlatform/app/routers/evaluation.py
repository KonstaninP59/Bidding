from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app import models, schemas
from app.dependencies import get_db, get_current_customer
from app.utils import scoring, audit
from typing import List

router = APIRouter(prefix="/api/evaluation", tags=["Оценка"])


@router.post("/manual-score")
def set_manual_score(
    score_input: schemas.ManualScoreInput,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    # Проверка прав на тендер
    proposal = db.query(models.Proposal).filter(models.Proposal.id == score_input.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Предложение не найдено")
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == proposal.round_id).first()
    tender = db.query(models.Tender).filter(models.Tender.id == round_obj.tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=403, detail="Нет доступа")

    # Находим значение критерия
    val = db.query(models.ProposalValue).filter(
        models.ProposalValue.proposal_id == score_input.proposal_id,
        models.ProposalValue.criterion_id == score_input.criterion_id
    ).first()
    if not val:
        raise HTTPException(status_code=404, detail="Значение критерия не найдено")

    val.value_numeric = score_input.score  # сохраняем балл
    val.value_text = score_input.comment
    db.commit()

    # Пересчитываем итоговый балл для всех предложений раунда
    recalc_round_scores(round_obj.id, db)

    audit.log_action(db, current_user.id, "MANUAL_SCORE", f"Proposal {proposal.id}", {"criterion": score_input.criterion_id, "score": score_input.score})
    return {"message": "Оценка сохранена"}


@router.post("/disqualify")
def disqualify_proposal(
    disqualify: schemas.DisqualifyInput,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    proposal = db.query(models.Proposal).filter(models.Proposal.id == disqualify.proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Предложение не найдено")
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == proposal.round_id).first()
    tender = db.query(models.Tender).filter(models.Tender.id == round_obj.tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=403, detail="Нет доступа")

    proposal.status = models.ProposalStatus.DISQUALIFIED
    proposal.disqualification_reason = disqualify.reason
    db.commit()

    audit.log_action(db, current_user.id, "DISQUALIFY", f"Proposal {proposal.id}", {"reason": disqualify.reason})
    return {"message": "Предложение дисквалифицировано"}


@router.post("/round/{round_id}/calculate")
def calculate_round_scores(
    round_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    recalc_round_scores(round_id, db)
    return {"message": "Баллы пересчитаны"}


def recalc_round_scores(round_id: int, db: Session):
    round_obj = db.query(models.TenderRound).filter(models.TenderRound.id == round_id).first()
    if not round_obj:
        return
    tender = db.query(models.Tender).filter(models.Tender.id == round_obj.tender_id).first()
    criteria = db.query(models.TenderCriterion).filter(models.TenderCriterion.tender_id == tender.id).all()
    proposals = db.query(models.Proposal).filter(
        models.Proposal.round_id == round_id,
        models.Proposal.status != models.ProposalStatus.DISQUALIFIED
    ).options(selectinload(models.Proposal.values)).all()

    # Собираем все значения для нормализации
    for p in proposals:
        p.final_score = scoring.calculate_final_score(p, criteria, proposals)

    # Сортируем и устанавливаем ранги
    sorted_props = sorted(proposals, key=lambda p: p.final_score or 0, reverse=True)
    for idx, p in enumerate(sorted_props, 1):
        p.rank = idx

    db.commit()
