from pydantic import BaseModel, EmailStr, Field, ConfigDict, validator
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.models import UserRole, SupplierStatus, TenderStatus, RoundStatus, ProposalStatus, CriterionType


# --- ОБЩИЕ ---
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


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    company_name: str


class UserResponse(UserBase):
    id: int
    is_active: bool
    role: UserRole
    company_id: Optional[int] = None
    model_config = ConfigDict(from_attributes=True)


# --- КОМПАНИИ ---
class CompanyBase(BaseModel):
    name: str
    inn: Optional[str] = None
    kpp: Optional[str] = None
    ogrn: Optional[str] = None
    address: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    accreditation_status: SupplierStatus
    accreditation_comment: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class CompanyDocumentBase(BaseModel):
    file_name: str
    expiry_date: Optional[datetime] = None


class CompanyDocumentResponse(CompanyDocumentBase):
    id: int
    file_path: str
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- ТЕНДЕРЫ ---
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
    scale: Optional[Dict[str, float]] = None  # для категориальных


class TenderCriterionResponse(TenderCriterionBase):
    id: int
    tender_id: int
    model_config = ConfigDict(from_attributes=True)


class TenderRoundBase(BaseModel):
    round_number: int
    end_time: datetime


class TenderRoundCreate(BaseModel):
    end_time: datetime
    allowed_supplier_ids: Optional[List[int]] = None  # для раунда 2+


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
    supplier_emails: List[EmailStr]  # кого пригласить

    @validator('first_round_deadline')
    def deadline_must_be_future(cls, v):
        if v <= datetime.utcnow():
            raise ValueError('Дедлайн должен быть в будущем')
        return v

    @validator('criteria')
    def weights_sum_to_100(cls, v):
        total = sum(c.weight for c in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError('Сумма весов критериев должна быть 100%')
        return v


class TenderPublish(BaseModel):
    pass  # можно добавить подтверждение


class TenderResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    currency: str
    status: TenderStatus
    created_at: datetime
    published_at: Optional[datetime]
    owner_id: int
    is_vendor_rank_visible: bool
    has_lots: bool
    items: List[TenderItemResponse] = []
    criteria: List[TenderCriterionResponse] = []
    rounds: List[TenderRoundResponse] = []
    model_config = ConfigDict(from_attributes=True)


# --- ПРИГЛАШЕНИЯ ---
class InvitationCheck(BaseModel):
    token: str


class InvitationResponse(BaseModel):
    tender_id: int
    tender_title: str
    supplier_email: str
    expires_at: datetime
    is_used: bool


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
    disqualification_reason: Optional[str]
    created_at: datetime
    supplier_id: int
    round_id: int
    values: List[ProposalValueResponse] = []
    files: List[ProposalFileResponse] = []
    model_config = ConfigDict(from_attributes=True)


# --- ОЦЕНКА ---
class ManualScoreInput(BaseModel):
    proposal_id: int
    criterion_id: int
    score: float = Field(..., ge=0, le=100)
    comment: Optional[str] = None


class DisqualifyInput(BaseModel):
    proposal_id: int
    reason: str


class WinnerSelect(BaseModel):
    proposal_id: int
    justification: str


# --- Q&A ---
class QuestionCreate(BaseModel):
    tender_id: int
    question_text: str
    is_public: bool = True


class QuestionResponse(BaseModel):
    id: int
    tender_id: int
    supplier_id: Optional[int]
    question_text: str
    is_public: bool
    created_at: datetime
    answers: List['AnswerResponse'] = []
    model_config = ConfigDict(from_attributes=True)


class AnswerCreate(BaseModel):
    question_id: int
    answer_text: str


class AnswerResponse(BaseModel):
    id: int
    question_id: int
    user_id: int
    answer_text: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# --- АУДИТ ---
class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    target_object: Optional[str]
    details: Optional[str]
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


# --- АНАЛИТИЧЕСКАЯ СПРАВКА (для передачи в шаблон) ---
class ReportData(BaseModel):
    tender: TenderResponse
    rounds: List[TenderRoundResponse]
    proposals: List[ProposalResponse]
    winner: Optional[ProposalResponse]
    model_config = ConfigDict(from_attributes=True)
