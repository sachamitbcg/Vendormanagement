"""ORM models.

Scoped to Process 3 (Vendor Risk & Onboarding Screener): `users`, `vendors`, and
`audit_log`. The brief lists tables for the other two processes
(`invoices`, `purchase_orders`, `budget_actuals`); those are intentionally omitted
here since this POC implements only Process 3 (see docs/design-decisions.md).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="analyst")  # analyst | reviewer
    created_at = Column(DateTime, default=_utcnow)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    abn = Column(String, index=True)            # tax ID / ABN — indexed for dup checks
    bank_account = Column(String, index=True)   # indexed for dup checks
    contact = Column(String)
    category = Column(String)

    # AI-written fields (the model fills these in; a human never types them).
    risk_tier = Column(String)                  # Low | Medium | High
    screening_notes = Column(Text)              # anomalies + verify checklist (JSON string)
    ai_rationale = Column(Text)

    # Human field.
    human_override = Column(String)             # reviewer's overriding tier, if any

    onboarding_status = Column(String, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime, default=_utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    entity_type = Column(String)   # e.g. "vendor"
    entity_id = Column(Integer)    # polymorphic pointer at vendors.id (not a formal FK)
    action = Column(String)        # ai_screen | override | approve | reject
    old_value = Column(Text)
    new_value = Column(Text)
    timestamp = Column(DateTime, default=_utcnow)
