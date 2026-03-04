from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator
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

# --- ТЕНДЕРЫ (вложенные схемы) ---
class TenderItemBase(BaseModel):
    name: str
    quantity: float
    unit: str
    requirements: Optional[str] = None


class TenderItemResponse(TenderItemBase):
    id: int
    tender_id: int
    model_config = ConfigDict(from_attributes=True)


class TenderCriterionBase(BaseModel):
    name: str
    weight: float = Field(..., ge=0, le=100)
    criterion_type: CriterionType
    is_mandatory: bool = False


class TenderCriterionResponse(TenderCriterionBase):
    id: int
    tender_id: int
    model_config = ConfigDict(from_attributes=True)


class TenderRoundBase(BaseModel):
    round_number: int
    end_time: datetime


class TenderRoundCreate(BaseModel):
    end_time: datetime


class TenderRoundResponse(TenderRoundBase):
    id: int
    tender_id: int
    start_time: datetime
    status: RoundStatus
    model_config = ConfigDict(from_attributes=True)


class TenderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    currency: str = "RUB"
    has_lots: bool = False
    is_vendor_rank_visible: bool = False
    
    items: List[TenderItemBase]
    criteria: List[TenderCriterionBase]
    
    first_round_deadline: datetime

    @validator('first_round_deadline')
    def deadline_must_be_future(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Deadline must be in the future')
        return v

    @validator('criteria')
    def weights_sum_to_100(cls, v):
        total = sum(c.weight for c in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError('Sum of criterion weights must be 100%')
        return v


class TenderResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    currency: str
    status: TenderStatus
    created_at: datetime
    owner_id: int
    is_vendor_rank_visible: bool
    has_lots: bool
    
    items: List[TenderItemResponse] = []
    criteria: List[TenderCriterionResponse] = []
    rounds: List[TenderRoundResponse] = []
    
    model_config = ConfigDict(from_attributes=True)

# --- ПРЕДЛОЖЕНИЯ ---
class ProposalValueCreate(BaseModel):
    criterion_id: int
    value_numeric: Optional[float] = None
    value_text: Optional[str] = None


class ProposalCreate(BaseModel):
    tender_id: int
    round_id: int
    values: List[ProposalValueCreate]


class ProposalValueResponse(BaseModel):
    id: int
    criterion_id: int
    value_numeric: Optional[float]
    value_text: Optional[str]
    score_normalized: Optional[float]
    model_config = ConfigDict(from_attributes=True)


class ProposalFileResponse(BaseModel):
    id: int
    file_name: str
    file_path: str
    model_config = ConfigDict(from_attributes=True)


class ProposalResponse(BaseModel):
    id: int
    status: ProposalStatus
    final_score: Optional[float]
    rank: Optional[int]
    created_at: datetime
    supplier_id: int
    round_id: int
    values: List[ProposalValueResponse] = []
    files: List[ProposalFileResponse] = []
    model_config = ConfigDict(from_attributes=True)
