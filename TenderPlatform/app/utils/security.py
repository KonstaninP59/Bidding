from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
import bcrypt
from app.config import settings

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, совпадает ли введённый пароль с хешем в БД.
    """
    # Берём первые 72 байта пароля (требование bcrypt)
    pw_bytes = plain_password.encode('utf-8')[:72]
    # Хеш из БД хранится как строка, преобразуем в байты
    return bcrypt.checkpw(pw_bytes, hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """
    Превращает пароль в хеш (bcrypt).
    Автоматически обрезает до 72 байт.
    """
    pw_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pw_bytes, salt)
    return hashed.decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Создаёт JWT токен для авторизации.
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
