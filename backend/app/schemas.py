"""Pydantic request/response models (the API contract)."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str
    role: str


# ---- Screening findings (from the rule engine) ----
class DuplicateMatch(BaseModel):
    vendor_id: int
    vendor_name: str
    match_type: str          # exact | partial
    matched_on: list[str]    # e.g. ["abn", "bank_account"]
    differs_on: list[str]


class ScreeningFindings(BaseModel):
    duplicates: list[DuplicateMatch]
    missing_fields: list[str]
    completeness_ok: bool
    highest_match: Optional[str] = None  # exact | partial | None


# ---- Vendor onboarding ----
class VendorSubmit(BaseModel):
    name: str = Field(min_length=1)
    abn: str = ""
    bank_account: str = ""
    contact: str = ""
    category: str = ""


class AIAssessment(BaseModel):
    risk_tier: str
    rationale: str
    anomalies: list[str] = []
    verify_checklist: list[str] = []
    source: str = "llm"          # llm | fallback
    llm_error: Optional[str] = None


class VendorOut(BaseModel):
    id: int
    name: str
    abn: Optional[str] = None
    bank_account: Optional[str] = None
    contact: Optional[str] = None
    category: Optional[str] = None
    risk_tier: Optional[str] = None
    human_override: Optional[str] = None
    effective_tier: Optional[str] = None
    onboarding_status: str
    ai_rationale: Optional[str] = None
    anomalies: list[str] = []
    verify_checklist: list[str] = []
    ai_source: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScreenResponse(BaseModel):
    """Returned right after a vendor is submitted and screened."""
    vendor: VendorOut
    findings: ScreeningFindings
    assessment: AIAssessment


class OverrideRequest(BaseModel):
    risk_tier: Optional[str] = None                 # reviewer's overriding tier
    onboarding_status: Optional[str] = None         # approved | rejected | pending


# ---- Dashboard ----
class AuditEntry(BaseModel):
    id: int
    user_email: Optional[str]
    entity_type: str
    entity_id: int
    action: str
    old_value: Optional[str]
    new_value: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_vendors: int
    by_tier: dict[str, int]
    by_status: dict[str, int]
    ai_decisions: int
    human_overrides: int
    override_rate: float
