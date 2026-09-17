"""ORM models.

The brief mandates six tables (section 3.3). Process 3 (Vendor Screener) actively
exercises `users`, `vendors`, and `audit_log`. The remaining three
(`invoices`, `purchase_orders`, `budget_actuals`) are created so the schema matches
the brief exactly, but are not used by this POC — this is a deliberate, documented
scope decision (see docs/design-decisions.md and the diagram's "schema present, not
exercised" note).
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
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


# ---------------------------------------------------------------------------
# Schema present to match the brief (section 3.3) but NOT exercised by Process 3.
# ---------------------------------------------------------------------------
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True)
    po_number = Column(String, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    approved_amount = Column(Float)
    cost_centre = Column(String)
    status = Column(String)


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    po_number = Column(String)
    amount = Column(Float)
    status = Column(String)
    ai_recommendation = Column(String)
    ai_rationale = Column(Text)
    human_override = Column(String)
    created_at = Column(DateTime, default=_utcnow)


class BudgetActual(Base):
    __tablename__ = "budget_actuals"

    id = Column(Integer, primary_key=True)
    cost_centre = Column(String)
    period = Column(String)
    budget_amount = Column(Float)
    actual_amount = Column(Float)
    variance_pct = Column(Float)
    narrative = Column(Text)
    narrative_approved = Column(String)
    approved_by = Column(String)
