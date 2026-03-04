from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional, Any
from datetime import datetime
from app.models import UserRole, SupplierStatus, TenderStatus, RoundStatus, ProposalStatus, CriterionType

# --- ОБЩИЕ СХЕМЫ ---

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- ПОЛЬЗОВАТЕЛИ ---

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    role: UserRole = UserRole.SUPPLIER

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    is_active: bool
    company_id: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

# --- КОМПАНИИ ---

class CompanyBase(BaseModel):
    name: str
    inn: Optional[str] = None
    kpp: Optional[str] = None
    address: Optional[str] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyResponse(CompanyBase):
    id: int
    accreditation_status: SupplierStatus
    
    model_config = ConfigDict(from_attributes=True)

# --- ТЕНДЕРЫ ---

class TenderItemBase(BaseModel):
    name: str
    quantity: float
    unit: str
    requirements: Optional[str] = None

class TenderCriterionBase(BaseModel):
    name: str
    weight: float
    criterion_type: CriterionType
    is_mandatory: bool = False

class TenderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    currency: str = "RUB"
    has_lots: bool = False
    is_vendor_rank_visible: bool = False
    
    items: List[TenderItemBase]
    criteria: List[TenderCriterionBase]
    
    # Дедлайн первого раунда
    first_round_deadline: datetime

class TenderResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    currency: str
    status: TenderStatus
    created_at: datetime
    owner_id: int
    is_vendor_rank_visible: bool
    
    # Вложенные объекты (для удобства отображения)
    items: List[Any] = [] # TenderItemResponse
    criteria: List[Any] = [] # TenderCriterionResponse
    rounds: List[Any] = [] # TenderRoundResponse
    
    model_config = ConfigDict(from_attributes=True)

# --- РАУНДЫ ---

class RoundCreate(BaseModel):
    end_time: datetime

class RoundResponse(BaseModel):
    id: int
    round_number: int
    start_time: datetime
    end_time: datetime
    status: RoundStatus
    
    model_config = ConfigDict(from_attributes=True)

# --- ПРЕДЛОЖЕНИЯ (PROPOSALS) ---

class ProposalValueCreate(BaseModel):
    criterion_id: int
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None

class ProposalCreate(BaseModel):
    tender_id: int
    round_id: int
    values: List[ProposalValueCreate]

class ProposalResponse(BaseModel):
    id: int
    status: ProposalStatus
    final_score: Optional[float]
    rank: Optional[int]
    created_at: datetime
    supplier_id: int
    
    model_config = ConfigDict(from_attributes=True)
