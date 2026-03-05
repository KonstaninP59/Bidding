from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload
from app import models, schemas
from app.dependencies import get_db, get_current_active_user, get_current_customer
from datetime import datetime
from app.utils import notifications, audit

router = APIRouter(prefix="/api/qna", tags=["Вопросы и ответы"])


@router.post("/questions", response_model=schemas.QuestionResponse)
def create_question(
    q: schemas.QuestionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    tender = db.query(models.Tender).filter(models.Tender.id == q.tender_id).first()
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")

    question = models.Question(
        tender_id=q.tender_id,
        supplier_id=current_user.id if current_user.role == models.UserRole.SUPPLIER else None,
        question_text=q.question_text,
        is_public=q.is_public,
        created_at=datetime.utcnow()
    )
    db.add(question)
    db.commit()
    db.refresh(question)

    # Уведомление заказчику (если нужно)
    # ...

    audit.log_action(db, current_user.id, "CREATE_QUESTION", f"Tender {q.tender_id}", {"question": q.question_text[:50]})
    return question


@router.post("/answers", response_model=schemas.AnswerResponse)
def create_answer(
    a: schemas.AnswerCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_customer)
):
    question = db.query(models.Question).filter(models.Question.id == a.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Вопрос не найден")
    tender = db.query(models.Tender).filter(models.Tender.id == question.tender_id, models.Tender.owner_id == current_user.id).first()
    if not tender:
        raise HTTPException(status_code=403, detail="Нет доступа")

    answer = models.Answer(
        question_id=a.question_id,
        user_id=current_user.id,
        answer_text=a.answer_text,
        created_at=datetime.utcnow()
    )
    db.add(answer)
    db.commit()
    db.refresh(answer)

    # Уведомление автору вопроса, если он есть
    if question.supplier_id:
        supplier = db.query(models.User).filter(models.User.id == question.supplier_id).first()
        if supplier:
            notifications.send_email(supplier.email, "Ответ на ваш вопрос", f"По тендеру {tender.title} получен ответ: {a.answer_text}")

    audit.log_action(db, current_user.id, "ANSWER_QUESTION", f"Question {a.question_id}")
    return answer

@router.get("/tender/{tender_id}", response_model=List[schemas.QuestionResponse])
def get_questions(tender_id: int, db: Session = Depends(get_db)):
    questions = db.query(models.Question).filter(
        models.Question.tender_id == tender_id,
        models.Question.is_public == True
    ).options(selectinload(models.Question.answers)).all()
    return questions
