"""Audit logging — every AI decision and every human override is recorded.

Design principle 6.2: "Log every AI decision and every human override. If you cannot
measure override rate, you cannot improve the model."
"""
from typing import Optional

from sqlalchemy.orm import Session

from .models import AuditLog


def record(
    db: Session,
    *,
    user_id: Optional[int],
    entity_type: str,
    entity_id: int,
    action: str,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    commit: bool = True,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        old_value=old_value,
        new_value=new_value,
    )
    db.add(entry)
    if commit:
        db.commit()
    return entry
