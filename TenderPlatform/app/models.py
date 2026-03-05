from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, Enum, Index, JSON
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime


# --- ENUMS ---
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"


class SupplierStatus(str, enum.Enum):
    DRAFT = "draft"
    ON_CHECK = "on_check"
    ACCREDITED = "accredited"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class TenderStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    EVALUATION = "evaluation"
    CLOSED = "closed"
    CANCELED = "canceled"


class RoundStatus(str, enum.Enum):
    PLANNED = "planned"
    ACTIVE = "active"
    COMPLETED = "completed"


class ProposalStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    FIXED = "fixed"
    DISQUALIFIED = "disqualified"


class CriterionType(str, enum.Enum):
    NUMERIC_MIN = "numeric_min"
    NUMERIC_MAX = "numeric_max"
    CATEGORICAL = "categorical"
    MANUAL = "manual"


# --- ТАБЛИЦЫ ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.SUPPLIER)
    full_name = Column(String, nullable=True)
    position = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    sent_messages = relationship("EmailLog", back_populates="user")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    inn = Column(String, index=True, nullable=True)
    kpp = Column(String, nullable=True)
    ogrn = Column(String, nullable=True)
    address = Column(String, nullable=True)
    accreditation_status = Column(Enum(SupplierStatus), default=SupplierStatus.DRAFT)
    accreditation_comment = Column(Text, nullable=True)
    users = relationship("User", back_populates="company")
    documents = relationship("CompanyDocument", back_populates="company")


class CompanyDocument(Base):
    __tablename__ = "company_documents"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    expiry_date = Column(DateTime, nullable=True)  # срок действия документа
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    company = relationship("Company", back_populates="documents")


class Tender(Base):
    __tablename__ = "tenders"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String, default="RUB")
    has_lots = Column(Boolean, default=False)
    is_vendor_rank_visible = Column(Boolean, default=False)
    status = Column(Enum(TenderStatus), default=TenderStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    published_at = Column(DateTime, nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"))
    winner_proposal_id = Column(Integer, nullable=True)
    winner_justification = Column(Text, nullable=True)

    owner = relationship("User", foreign_keys=[owner_id])
    items = relationship("TenderItem", back_populates="tender", cascade="all, delete-orphan")
    rounds = relationship("TenderRound", back_populates="tender", order_by="TenderRound.round_number", cascade="all, delete-orphan")
    criteria = relationship("TenderCriterion", back_populates="tender", cascade="all, delete-orphan")
    invitations = relationship("TenderInvitation", back_populates="tender", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="tender", cascade="all, delete-orphan")

    __table_args__ = (Index('ix_tenders_status', 'status'),)


class TenderItem(Base):
    __tablename__ = "tender_items"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)
    requirements = Column(Text, nullable=True)
    tender = relationship("Tender", back_populates="items")


class TenderCriterion(Base):
    __tablename__ = "tender_criteria"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    weight = Column(Float, nullable=False)  # в процентах
    criterion_type = Column(Enum(CriterionType), default=CriterionType.NUMERIC_MIN)
    is_mandatory = Column(Boolean, default=False)
    # Для категориального критерия можно хранить шкалу в JSON
    scale = Column(JSON, nullable=True)  # например {"Отлично": 100, "Хорошо": 50, "Плохо": 0}
    tender = relationship("Tender", back_populates="criteria")
    proposal_values = relationship("ProposalValue", back_populates="criterion")


class TenderRound(Base):
    __tablename__ = "tender_rounds"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    round_number = Column(Integer, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=False)
    status = Column(Enum(RoundStatus), default=RoundStatus.PLANNED)
    tender = relationship("Tender", back_populates="rounds")
    proposals = relationship("Proposal", back_populates="round", cascade="all, delete-orphan")
    # Список допущенных поставщиков (для раундов 2+)
    allowed_suppliers = relationship("RoundAllowedSupplier", back_populates="round", cascade="all, delete-orphan")
    __table_args__ = (Index('ix_rounds_end_time', 'end_time'),)


class RoundAllowedSupplier(Base):
    __tablename__ = "round_allowed_suppliers"
    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("tender_rounds.id", ondelete="CASCADE"))
    supplier_id = Column(Integer, ForeignKey("users.id"))
    round = relationship("TenderRound", back_populates="allowed_suppliers")
    supplier = relationship("User")


class TenderInvitation(Base):
    __tablename__ = "tender_invitations"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    supplier_email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False)
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    tender = relationship("Tender", back_populates="invitations")


class Proposal(Base):
    __tablename__ = "proposals"
    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("tender_rounds.id", ondelete="CASCADE"))
    supplier_id = Column(Integer, ForeignKey("users.id"))
    status = Column(Enum(ProposalStatus), default=ProposalStatus.DRAFT)
    final_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    disqualification_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    round = relationship("TenderRound", back_populates="proposals")
    supplier = relationship("User")
    values = relationship("ProposalValue", back_populates="proposal", cascade="all, delete-orphan")
    files = relationship("ProposalFile", back_populates="proposal", cascade="all, delete-orphan")
    __table_args__ = (Index('ix_proposals_round_supplier', 'round_id', 'supplier_id', unique=True),)


class ProposalValue(Base):
    __tablename__ = "proposal_values"
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id", ondelete="CASCADE"))
    criterion_id = Column(Integer, ForeignKey("tender_criteria.id", ondelete="CASCADE"))
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    score_normalized = Column(Float, nullable=True)  # нормированный балл (0-100)
    proposal = relationship("Proposal", back_populates="values")
    criterion = relationship("TenderCriterion", back_populates="proposal_values")


class ProposalFile(Base):
    __tablename__ = "proposal_files"
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id", ondelete="CASCADE"))
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    proposal = relationship("Proposal", back_populates="files")


class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    supplier_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # может быть анонимным?
    question_text = Column(Text, nullable=False)
    is_public = Column(Boolean, default=True)  # видимость всем или только автору
    created_at = Column(DateTime, default=datetime.utcnow)
    tender = relationship("Tender", back_populates="questions")
    supplier = relationship("User")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id"))  # кто ответил (заказчик/админ)
    answer_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    question = relationship("Question", back_populates="answers")
    user = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    target_object = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="audit_logs")


class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    recipient = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body_preview = Column(String, nullable=True)
    status = Column(String, default="sent")  # sent/failed
    error = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="sent_messages")
