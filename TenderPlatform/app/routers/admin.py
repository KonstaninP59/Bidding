from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app import models, schemas
from app.dependencies import get_db, get_current_admin
from app.utils import files, notifications, audit
from datetime import datetime

router = APIRouter(prefix="/api/admin", tags=["Администрирование"])


@router.get("/suppliers", response_model=List[schemas.CompanyResponse])
def list_suppliers(
    status: models.SupplierStatus = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    query = db.query(models.Company)
    if status:
        query = query.filter(models.Company.accreditation_status == status)
    return query.all()


@router.post("/suppliers/{company_id}/accredit")
def accredit_supplier(
    company_id: int,
    status: models.SupplierStatus,
    comment: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Компания не найдена")
    company.accreditation_status = status
    company.accreditation_comment = comment
    db.commit()

    # Уведомить пользователей компании
    for user in company.users:
        notifications.send_accreditation_result(user.email, company.name, status.value, comment)

    audit.log_action(db, current_user.id, "ACCREDIT_SUPPLIER", f"Company {company_id}", {"status": status.value})
    return {"message": "Статус аккредитации обновлён"}


@router.post("/suppliers/{company_id}/documents", response_model=schemas.CompanyDocumentResponse)
async def upload_company_document(
    company_id: int,
    file: UploadFile = File(...),
    expiry_date: datetime = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin)
):
    await files.validate_file(file)
    file_path = await files.save_upload_file(file, subfolder="company_docs")
    doc = models.CompanyDocument(
        company_id=company_id,
        file_path=file_path,
        file_name=file.filename,
        expiry_date=expiry_date
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/users", response_model=List[schemas.UserResponse])
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin)):
    return db.query(models.User).all()


@router.post("/users/{user_id}/block")
def block_user(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_admin)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = not user.is_active  # переключение
    db.commit()
    audit.log_action(db, current_user.id, "TOGGLE_USER_BLOCK", f"User {user_id}", {"active": user.is_active})
    return {"message": f"Пользователь {'разблокирован' if user.is_active else 'заблокирован'}"}
