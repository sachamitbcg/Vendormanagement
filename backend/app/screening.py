"""Deterministic screening engine (runs BEFORE the LLM).

This is the "Screening Engine" box in the architecture diagram. It queries the existing
vendor master for duplicates and validates completeness, producing structured findings.
Those findings are (a) shown to the reviewer and (b) handed to the LLM gateway as ground
truth. Keeping this rule-based and separate from the model means duplicate detection is
100% reproducible and never "invented" by the AI.
"""
import re
from typing import Optional

from sqlalchemy.orm import Session

from .models import Vendor
from .schemas import DuplicateMatch, ScreeningFindings, VendorSubmit

REQUIRED_FIELDS = {
    "name": "vendor name",
    "abn": "tax ID / ABN",
    "bank_account": "bank account",
    "category": "category",
}


def _normalise(value: Optional[str]) -> str:
    """Strip spaces, punctuation and case so '12 345 678 901' == '12345678901'
    and 'BSB 062-000 / 12345678' compares on its digits."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _missing_fields(vendor: VendorSubmit) -> list[str]:
    missing = []
    for field, label in REQUIRED_FIELDS.items():
        if not (getattr(vendor, field, "") or "").strip():
            missing.append(label)
    return missing


def screen(db: Session, submitted: VendorSubmit) -> ScreeningFindings:
    sub_abn = _normalise(submitted.abn)
    sub_bank = _normalise(submitted.bank_account)

    duplicates: list[DuplicateMatch] = []

    # Only compare against vendors that have something to compare on.
    for existing in db.query(Vendor).all():
        ex_abn = _normalise(existing.abn)
        ex_bank = _normalise(existing.bank_account)

        abn_match = bool(sub_abn) and sub_abn == ex_abn
        bank_match = bool(sub_bank) and sub_bank == ex_bank
        if not (abn_match or bank_match):
            continue

        matched_on = []
        differs_on = []
        if abn_match:
            matched_on.append("abn")
        elif sub_abn and ex_abn:
            differs_on.append("abn")
        if bank_match:
            matched_on.append("bank_account")
        elif sub_bank and ex_bank:
            differs_on.append("bank_account")

        # Exact = both key identifiers line up; partial = one matches, one differs.
        match_type = "exact" if abn_match and bank_match else "partial"

        duplicates.append(
            DuplicateMatch(
                vendor_id=existing.id,
                vendor_name=existing.name,
                match_type=match_type,
                matched_on=matched_on,
                differs_on=differs_on,
            )
        )

    missing = _missing_fields(submitted)

    highest = None
    if any(d.match_type == "exact" for d in duplicates):
        highest = "exact"
    elif duplicates:
        highest = "partial"

    return ScreeningFindings(
        duplicates=duplicates,
        missing_fields=missing,
        completeness_ok=len(missing) == 0,
        highest_match=highest,
    )


def findings_to_text(findings: ScreeningFindings) -> str:
    """Render findings as the plain-text block injected into the LLM user prompt."""
    lines: list[str] = []
    if findings.duplicates:
        for d in findings.duplicates:
            matched = ", ".join(d.matched_on) or "none"
            differs = ", ".join(d.differs_on) or "none"
            lines.append(
                f"- {d.match_type.upper()} DUPLICATE of existing vendor "
                f"'{d.vendor_name}' (ID {d.vendor_id}): matches on [{matched}], "
                f"differs on [{differs}]."
            )
    else:
        lines.append("- No duplicate match against the existing vendor master.")

    if findings.missing_fields:
        lines.append(
            "- Incomplete submission — missing required field(s): "
            + ", ".join(findings.missing_fields)
            + "."
        )
    else:
        lines.append("- All required fields are present.")

    return "\n".join(lines)


def fallback_tier(findings: ScreeningFindings) -> str:
    """Rule-only risk tier, used when the LLM is unavailable (design 3.2 / 6.4)."""
    if findings.highest_match == "exact":
        return "High"
    if findings.highest_match == "partial" or not findings.completeness_ok:
        return "Medium"
    return "Low"
