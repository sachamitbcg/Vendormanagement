"""Vendor onboarding & master — the core of Process 3."""
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import audit, llm_gateway, screening
from ..database import get_db
from ..deps import get_current_user, require_reviewer
from ..models import User, Vendor
from ..schemas import (
    AIAssessment,
    OverrideRequest,
    ScreenResponse,
    VendorOut,
    VendorSubmit,
)

router = APIRouter(prefix="/api/vendors", tags=["vendors"])

VALID_TIERS = {"Low", "Medium", "High"}
VALID_STATUS = {"pending", "approved", "rejected"}


def _to_out(v: Vendor) -> VendorOut:
    """Build the API view, unpacking the AI notes JSON stored on the row."""
    notes = {}
    if v.screening_notes:
        try:
            notes = json.loads(v.screening_notes)
        except json.JSONDecodeError:
            notes = {}
    effective = v.human_override or v.risk_tier
    return VendorOut(
        id=v.id,
        name=v.name,
        abn=v.abn,
        bank_account=v.bank_account,
        contact=v.contact,
        category=v.category,
        risk_tier=v.risk_tier,
        human_override=v.human_override,
        effective_tier=effective,
        onboarding_status=v.onboarding_status,
        ai_rationale=v.ai_rationale,
        anomalies=notes.get("anomalies", []),
        verify_checklist=notes.get("verify_checklist", []),
        ai_source=notes.get("source"),
        created_at=v.created_at,
    )


@router.post("", response_model=ScreenResponse, status_code=status.HTTP_201_CREATED)
def submit_vendor(
    payload: VendorSubmit,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Submit a vendor: run the rule engine, then the LLM, persist, and audit.

    The AI output is *stored*, never discarded (design 3.2), and the vendor is created
    as `pending` — nothing is auto-approved (design 6.2)."""
    findings = screening.screen(db, payload)
    assessment: AIAssessment = llm_gateway.assess(payload, findings)

    vendor = Vendor(
        name=payload.name,
        abn=payload.abn,
        bank_account=payload.bank_account,
        contact=payload.contact,
        category=payload.category,
        risk_tier=assessment.risk_tier,
        ai_rationale=assessment.rationale,
        screening_notes=json.dumps(
            {
                "anomalies": assessment.anomalies,
                "verify_checklist": assessment.verify_checklist,
                "source": assessment.source,
                "llm_error": assessment.llm_error,
            }
        ),
        human_override=None,
        onboarding_status="pending",
    )
    db.add(vendor)
    db.commit()
    db.refresh(vendor)

    audit.record(
        db,
        user_id=user.id,
        entity_type="vendor",
        entity_id=vendor.id,
        action="ai_screen",
        old_value=None,
        new_value=f"{assessment.risk_tier} ({assessment.source})",
    )

    return ScreenResponse(
        vendor=_to_out(vendor), findings=findings, assessment=assessment
    )


@router.get("", response_model=list[VendorOut])
def list_vendors(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    vendors = db.query(Vendor).order_by(Vendor.created_at.desc(), Vendor.id.desc()).all()
    return [_to_out(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found.")
    return _to_out(vendor)


@router.patch("/{vendor_id}", response_model=VendorOut)
def override_vendor(
    vendor_id: int,
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    reviewer: User = Depends(require_reviewer),
):
    """Reviewer overrides the AI tier and/or sets the onboarding decision.

    Every override is written to the audit log so override-rate can be measured
    (design 6.2)."""
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vendor not found.")

    if payload.risk_tier is not None:
        if payload.risk_tier not in VALID_TIERS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid risk tier.")
        old = vendor.human_override or vendor.risk_tier
        vendor.human_override = payload.risk_tier
        audit.record(
            db,
            user_id=reviewer.id,
            entity_type="vendor",
            entity_id=vendor.id,
            action="override",
            old_value=f"AI: {vendor.risk_tier} / effective: {old}",
            new_value=payload.risk_tier,
            commit=False,
        )

    if payload.onboarding_status is not None:
        if payload.onboarding_status not in VALID_STATUS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid status.")
        old_status = vendor.onboarding_status
        vendor.onboarding_status = payload.onboarding_status
        audit.record(
            db,
            user_id=reviewer.id,
            entity_type="vendor",
            entity_id=vendor.id,
            action=payload.onboarding_status,  # approved | rejected | pending
            old_value=old_status,
            new_value=payload.onboarding_status,
            commit=False,
        )

    db.commit()
    db.refresh(vendor)
    return _to_out(vendor)
