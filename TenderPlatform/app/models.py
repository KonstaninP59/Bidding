from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, Text, Enum, func
from sqlalchemy.orm import relationship
from app.database import Base
import enum
from datetime import datetime

# --- ENUMS (Справочники статусов из ТЗ) ---

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    CUSTOMER = "customer" # Заказчик
    SUPPLIER = "supplier" # Поставщик

class SupplierStatus(str, enum.Enum):
    DRAFT = "draft"             # Черновик
    ON_CHECK = "on_check"       # На проверке
    ACCREDITED = "accredited"   # Аккредитован
    REJECTED = "rejected"       # Отказ
    SUSPENDED = "suspended"     # Приостановлен

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
    FIXED = "fixed" # Зафиксировано после дедлайна
    DISQUALIFIED = "disqualified"

class CriterionType(str, enum.Enum):
    NUMERIC_MIN = "numeric_min" # Цена, Срок (чем меньше, тем лучше)
    NUMERIC_MAX = "numeric_max" # Гарантия (чем больше, тем лучше)
    CATEGORICAL = "categorical" # Выбор из списка
    MANUAL = "manual"           # Ручная оценка

# --- ТАБЛИЦЫ ---

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.SUPPLIER)
    
    full_name = Column(String, nullable=True)
    position = Column(String, nullable=True) # Должность
    phone = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Связь с компанией (один юзер принадлежит одной компании/поставщику)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    company = relationship("Company", back_populates="users")

    # Для аудита
    audit_logs = relationship("AuditLog", back_populates="user")


class Company(Base):
    """
    Сущность для Поставщика или Организации Заказчика.
    """
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    inn = Column(String, index=True, nullable=True) # ИНН
    kpp = Column(String, nullable=True)
    address = Column(String, nullable=True)
    
    # Статус аккредитации (важно для поставщиков)
    accreditation_status = Column(Enum(SupplierStatus), default=SupplierStatus.DRAFT)
    accreditation_comment = Column(Text, nullable=True) # Комментарий админа при отказе

    users = relationship("User", back_populates="company")
    # Файлы аккредитации
    documents = relationship("CompanyDocument", back_populates="company")


class CompanyDocument(Base):
    __tablename__ = "company_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True) # Устав, Выписка и т.д.
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    company = relationship("Company", back_populates="documents")


class Tender(Base):
    __tablename__ = "tenders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String, default="RUB")
    
    # Настройки
    has_lots = Column(Boolean, default=False) # С лотами или без
    is_vendor_rank_visible = Column(Boolean, default=False) # Видит ли поставщик свое место
    
    status = Column(Enum(TenderStatus), default=TenderStatus.DRAFT)
    created_at = Column(DateTime, default=datetime.utcnow)
    owner_id = Column(Integer, ForeignKey("users.id")) # Кто создал (Заказчик)

    # Связи
    items = Column(Text, nullable=True) # Если без лотов, позиции могут быть тут или в items (упростим: всегда используем таблицу TenderItem)
    rounds = relationship("TenderRound", back_populates="tender", order_by="TenderRound.round_number")
    criteria = relationship("TenderCriterion", back_populates="tender")
    invitations = relationship("TenderInvitation", back_populates="tender")
    
    # Для аналитики
    winner_proposal_id = Column(Integer, nullable=True) # ID победившего предложения
    winner_justification = Column(Text, nullable=True) # Обоснование выбора


class TenderItem(Base):
    """Позиция в тендере (Товар/Услуга)"""
    __tablename__ = "tender_items"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False) # Ед. измерения (шт, кг)
    requirements = Column(Text, nullable=True) # Тех. требования


class TenderCriterion(Base):
    """Критерии оценки"""
    __tablename__ = "tender_criteria"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    
    name = Column(String, nullable=False) # Цена, Срок поставки...
    weight = Column(Float, nullable=False) # Вес % (сумма должна быть 100)
    criterion_type = Column(Enum(CriterionType), default=CriterionType.NUMERIC_MIN)
    is_mandatory = Column(Boolean, default=False) # Обязательный (pass/fail)
    
    tender = relationship("Tender", back_populates="criteria")


class TenderRound(Base):
    """Раунды переторжки"""
    __tablename__ = "tender_rounds"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    
    round_number = Column(Integer, nullable=False) # 1, 2, 3...
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=False) # Дедлайн
    
    status = Column(Enum(RoundStatus), default=RoundStatus.PLANNED)
    
    tender = relationship("Tender", back_populates="rounds")
    proposals = relationship("Proposal", back_populates="round")


class TenderInvitation(Base):
    """Приглашения поставщиков"""
    __tablename__ = "tender_invitations"

    id = Column(Integer, primary_key=True, index=True)
    tender_id = Column(Integer, ForeignKey("tenders.id"))
    supplier_email = Column(String, nullable=False)
    token = Column(String, unique=True, nullable=False) # Уникальная ссылка
    is_used = Column(Boolean, default=False) # Использована ли ссылка
    
    tender = relationship("Tender", back_populates="invitations")


class Proposal(Base):
    """Предложение поставщика в конкретном раунде"""
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)
    round_id = Column(Integer, ForeignKey("tender_rounds.id"))
    supplier_id = Column(Integer, ForeignKey("users.id")) # Поставщик
    
    status = Column(Enum(ProposalStatus), default=ProposalStatus.DRAFT)
    final_score = Column(Float, nullable=True) # Итоговый балл Si
    rank = Column(Integer, nullable=True) # Занятое место
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    round = relationship("TenderRound", back_populates="proposals")
    values = relationship("ProposalValue", back_populates="proposal") # Ответы на критерии
    files = relationship("ProposalFile", back_populates="proposal")


class ProposalValue(Base):
    """Значение конкретного критерия в предложении (цена 100 руб, срок 5 дней)"""
    __tablename__ = "proposal_values"

    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"))
    criterion_id = Column(Integer, ForeignKey("tender_criteria.id"))
    
    value_numeric = Column(Float, nullable=True) # Если число
    value_text = Column(Text, nullable=True)     # Если текст/комментарий
    score_normalized = Column(Float, nullable=True) # Нормированный балл (0-100)
    
    proposal = relationship("Proposal", back_populates="values")


class ProposalFile(Base):
    __tablename__ = "proposal_files"
    
    id = Column(Integer, primary_key=True, index=True)
    proposal_id = Column(Integer, ForeignKey("proposals.id"))
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    
    proposal = relationship("Proposal", back_populates="files")


class AuditLog(Base):
    """Журнал аудита"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False) # "Создание тендера", "Вход"
    target_object = Column(String, nullable=True) # "Tender #1"
    details = Column(Text, nullable=True) # JSON или текст изменений
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="audit_logs")
