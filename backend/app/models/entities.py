import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def now():
    return datetime.now(timezone.utc)


def uid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="entrepreneur")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    company: Mapped["Company|None"] = relationship(
        back_populates="owner", uselist=False
    )


class SessionRecord(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    csrf_hash: Mapped[str] = mapped_column(String(64))
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    name: Mapped[str] = mapped_column(String(255))
    inn: Mapped[str] = mapped_column(String(12), index=True)
    legal_form: Mapped[str] = mapped_column(String(40))
    registered_at: Mapped[str] = mapped_column(String(10))
    industry: Mapped[str] = mapped_column(String(120))
    revenue: Mapped[float] = mapped_column(Float, default=0)
    expenses: Mapped[float] = mapped_column(Float, default=0)
    obligations: Mapped[float] = mapped_column(Float, default=0)
    overdue: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )

    owner: Mapped[User] = relationship(back_populates="company")


class CreditProduct(Base):
    __tablename__ = "credit_products"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    version: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(30))
    purpose: Mapped[str] = mapped_column(Text)
    min_amount: Mapped[int] = mapped_column(Integer)
    max_amount: Mapped[int] = mapped_column(Integer)
    min_term: Mapped[int] = mapped_column(Integer)
    max_term: Mapped[int] = mapped_column(Integer)
    rate: Mapped[float] = mapped_column(Float)
    min_age_months: Mapped[int] = mapped_column(Integer)
    min_revenue: Mapped[int] = mapped_column(Integer)
    required_document: Mapped[str] = mapped_column(String(30))
    extras: Mapped[str] = mapped_column(Text)
    limit_text: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class LoanApplication(Base):
    __tablename__ = "loan_applications"

    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        default=lambda: "AH-" + uuid.uuid4().hex[:12].upper(),
    )
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("credit_products.id"))
    product_version: Mapped[str] = mapped_column(String(40))
    purpose: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30))
    amount: Mapped[int] = mapped_column(Integer)
    term: Mapped[int] = mapped_column(Integer)
    company_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, onupdate=now
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    documents: Mapped[list["ApplicationDocument"]] = relationship(
        cascade="all, delete-orphan"
    )
    history: Mapped[list["StatusHistory"]] = relationship(
        cascade="all, delete-orphan", order_by="StatusHistory.created_at"
    )
    checks: Mapped[list["BankCheckResult"]] = relationship(cascade="all, delete-orphan")
    decision: Mapped["CreditDecision|None"] = relationship(
        cascade="all, delete-orphan", uselist=False
    )


class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(255))
    mime: Mapped[str] = mapped_column(String(100))
    size: Mapped[int] = mapped_column(Integer)
    storage_path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class StatusHistory(Base):
    __tablename__ = "application_status_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class BankCheckResult(Base):
    __tablename__ = "bank_check_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"), index=True
    )
    attempt: Mapped[int] = mapped_column(Integer)
    fns: Mapped[str] = mapped_column(Text)
    bki: Mapped[str] = mapped_column(Text)
    financial: Mapped[str] = mapped_column(Text)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_reasons: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class CreditDecision(Base):
    __tablename__ = "credit_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("loan_applications.id", ondelete="CASCADE"), unique=True
    )
    outcome: Mapped[str] = mapped_column(String(30))
    approved: Mapped[bool] = mapped_column(Boolean)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    rate: Mapped[float] = mapped_column(Float)
    monthly_payment: Mapped[float] = mapped_column(Float)
    note: Mapped[str] = mapped_column(Text)
    rule_version: Mapped[str] = mapped_column(String(40), default="rules-1.0")
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    application_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    action: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
