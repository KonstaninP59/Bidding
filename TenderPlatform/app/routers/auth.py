from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app import models, schemas, database
from app.utils import security
from app.dependencies import get_db

router = APIRouter(tags=["Authentication"])

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрация нового пользователя (Поставщика).
    Сразу создается и Компания-черновик.
    """
    # 1. Проверяем, есть ли такой email
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # 2. Создаем компанию (пока пустую, пользователь заполнит потом)
    new_company = models.Company(name=f"Company of {user.full_name}")
    db.add(new_company)
    db.commit()
    db.refresh(new_company)

    # 3. Создаем пользователя
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        role=models.UserRole.SUPPLIER, # По умолчанию - поставщик
        company_id=new_company.id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Вход в систему. Возвращает JWT токен.
    username здесь = email.
    """
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # Проверка пароля
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Генерация токена
    access_token_expires = timedelta(minutes=30) # 30 минут жизни токена
    access_token = security.create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}
