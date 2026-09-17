"""Dashboard — vendor master stats + the eval log (AI vs human override rate)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AuditLog, User, Vendor
from ..schemas import AuditEntry, DashboardStats

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
def stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vendors = db.query(Vendor).all()

    by_tier = {"Low": 0, "Medium": 0, "High": 0}
    by_status = {"pending": 0, "approved": 0, "rejected": 0}
    for v in vendors:
        effective = v.human_override or v.risk_tier
        if effective in by_tier:
            by_tier[effective] += 1
        if v.onboarding_status in by_status:
            by_status[v.onboarding_status] += 1

    ai_decisions = db.query(AuditLog).filter(AuditLog.action == "ai_screen").count()
    overrides = db.query(AuditLog).filter(AuditLog.action == "override").count()
    rate = (overrides / ai_decisions) if ai_decisions else 0.0

    return DashboardStats(
        total_vendors=len(vendors),
        by_tier=by_tier,
        by_status=by_status,
        ai_decisions=ai_decisions,
        human_overrides=overrides,
        override_rate=round(rate, 3),
    )


@router.get("/audit", response_model=list[AuditEntry])
def audit_log(
    limit: int = 100,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """The eval log — every AI decision and human override, newest first."""
    rows = (
        db.query(AuditLog, User.email)
        .outerjoin(User, AuditLog.user_id == User.id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .limit(limit)
        .all()
    )
    return [
        AuditEntry(
            id=log.id,
            user_email=email,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            old_value=log.old_value,
            new_value=log.new_value,
            timestamp=log.timestamp,
        )
        for log, email in rows
    ]
