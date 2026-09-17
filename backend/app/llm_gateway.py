"""LLM Gateway — the only place that talks to Claude.

Responsibilities (matches the "LLM Gateway" box in the architecture diagram):
  1. Load the externalised prompt from /prompts/vendor_screening.md (design 6.3 — prompts
     are never hardcoded in route handlers).
  2. Call Claude with a system + user message and a structured JSON output schema.
  3. Validate the reply; retry once on a transient failure.
  4. On timeout / rate-limit / bad JSON: fall back to the rule-based tier and surface the
     error so the UI can show a banner (design 3.2 / 6.4 — handle LLM failure gracefully,
     never auto-approve).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from .config import PROMPTS_DIR, get_settings
from .schemas import AIAssessment, ScreeningFindings, VendorSubmit
from .screening import fallback_tier, findings_to_text

settings = get_settings()
_PROMPT_PATH = PROMPTS_DIR / "vendor_screening.md"


# ---------------------------------------------------------------------------
# Prompt loading / parsing
# ---------------------------------------------------------------------------
def _load_prompt() -> tuple[str, str, dict]:
    """Parse SYSTEM text, USER template, and the JSON response schema out of the
    externalised markdown prompt file."""
    text = _PROMPT_PATH.read_text(encoding="utf-8")

    def _section(header: str, stop_headers: list[str]) -> str:
        # capture everything after "## <header>" up to the next listed header / '---'
        pattern = rf"##\s+{re.escape(header)}\s*\n(.*?)(?=\n##\s+(?:{'|'.join(stop_headers)})|\n---)"
        m = re.search(pattern, text, re.DOTALL)
        return m.group(1).strip() if m else ""

    system = _section("SYSTEM", ["USER", "RESPONSE_SCHEMA"])
    user = _section("USER", ["RESPONSE_SCHEMA"])

    schema_match = re.search(
        r"##\s+RESPONSE_SCHEMA\s*\n```json\s*\n(.*?)\n```", text, re.DOTALL
    )
    schema = json.loads(schema_match.group(1)) if schema_match else {}
    return system, user, schema


# Parsed once at import — the prompt is static, so this also keeps the cache prefix stable.
try:
    SYSTEM_PROMPT, USER_TEMPLATE, RESPONSE_SCHEMA = _load_prompt()
except (OSError, ValueError) as exc:  # pragma: no cover
    SYSTEM_PROMPT, USER_TEMPLATE, RESPONSE_SCHEMA = "", "", {}
    _LOAD_ERROR = str(exc)
else:
    _LOAD_ERROR = None


def _build_user_message(vendor: VendorSubmit, findings: ScreeningFindings) -> str:
    return USER_TEMPLATE.format(
        name=vendor.name or "(blank)",
        abn=vendor.abn or "(blank)",
        bank_account=vendor.bank_account or "(blank)",
        contact=vendor.contact or "(blank)",
        category=vendor.category or "(blank)",
        findings=findings_to_text(findings),
    )


# ---------------------------------------------------------------------------
# Fallback assessment (no LLM)
# ---------------------------------------------------------------------------
def _fallback(findings: ScreeningFindings, error: Optional[str]) -> AIAssessment:
    tier = fallback_tier(findings)
    anomalies: list[str] = []
    checklist: list[str] = []

    for d in findings.duplicates:
        if d.match_type == "exact":
            anomalies.append(
                f"Exact duplicate of existing vendor '{d.vendor_name}' "
                f"(same tax ID and bank account)"
            )
            checklist.append(
                f"Confirm whether '{d.vendor_name}' is the same entity before creating a "
                f"second record or payment route."
            )
        else:
            anomalies.append(
                f"Partial duplicate of '{d.vendor_name}' "
                f"(shares {', '.join(d.matched_on)}, differs on {', '.join(d.differs_on)})"
            )
            checklist.append(
                f"Verify the differing detail against '{d.vendor_name}' — could be a "
                f"legitimate second entity or a redirected bank account."
            )
    if findings.missing_fields:
        anomalies.append("Missing required field(s): " + ", ".join(findings.missing_fields))
        checklist.append("Request the missing details from the vendor before approving.")
    if not anomalies:
        checklist.append("Standard KYC / sanctions check; no anomalies detected by rules.")

    rationale = {
        "High": "Rule check found an exact duplicate - highest onboarding risk.",
        "Medium": "Rule check flagged a partial duplicate or an incomplete submission - needs review.",
        "Low": "No duplicate found and submission is complete.",
    }[tier]

    return AIAssessment(
        risk_tier=tier,
        rationale=rationale,
        anomalies=anomalies,
        verify_checklist=checklist,
        source="fallback",
        llm_error=error,
    )


# ---------------------------------------------------------------------------
# Claude call + JSON extraction
# ---------------------------------------------------------------------------
def _call_claude(client, anthropic_mod, user_message: str):
    """Call Claude asking for structured JSON.

    Best practice (design 6.3) is the API's structured-output feature
    (`output_config.format`). Newer SDKs support it; older ones raise TypeError for the
    unknown kwarg. Either way the prompt itself demands JSON matching the schema, so we
    degrade to a plain call and parse the JSON body — never regex free text.
    """
    common = dict(
        model=settings.claude_model,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    try:
        return client.messages.create(
            **common,
            output_config={"format": {"type": "json_schema", "schema": RESPONSE_SCHEMA}},
        )
    except TypeError:
        # SDK too old for output_config — the prompt still constrains the output to JSON.
        return client.messages.create(**common)


def _extract_json(text: str) -> str:
    """Pull the JSON object out of the model's text, tolerating ```json fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def assess(vendor: VendorSubmit, findings: ScreeningFindings) -> AIAssessment:
    """Return an AI risk assessment, or a rule-based fallback if the LLM is unavailable."""
    if not settings.llm_enabled or _LOAD_ERROR:
        reason = _LOAD_ERROR or "No ANTHROPIC_API_KEY configured — running in rule-only mode."
        return _fallback(findings, reason)

    # Imported lazily so the app boots even if the SDK isn't installed.
    import anthropic

    client = anthropic.Anthropic(
        api_key=settings.anthropic_api_key,
        timeout=settings.llm_timeout_seconds,
        max_retries=1,  # SDK retries transient 429/5xx once before raising
    )
    user_message = _build_user_message(vendor, findings)

    last_error: Optional[str] = None
    for attempt in range(2):  # one manual retry on top of the SDK's own retry
        try:
            resp = _call_claude(client, anthropic, user_message)
            text = next((b.text for b in resp.content if b.type == "text"), "")
            data = json.loads(_extract_json(text))
            return AIAssessment(
                risk_tier=data["risk_tier"],
                rationale=data["rationale"],
                anomalies=data.get("anomalies", []),
                verify_checklist=data.get("verify_checklist", []),
                source="llm",
            )
        except anthropic.APIStatusError as exc:
            last_error = f"Claude API error {exc.status_code}: {exc.message}"
            if exc.status_code and 400 <= exc.status_code < 500 and exc.status_code != 429:
                break  # client error won't fix itself on retry
        except anthropic.APIConnectionError:
            last_error = "Could not reach Claude (network error)."
        except anthropic.APITimeoutError:
            last_error = f"Claude timed out after {settings.llm_timeout_seconds:.0f}s."
        except (json.JSONDecodeError, KeyError, StopIteration):
            last_error = "Claude returned a response that did not match the schema."
        except Exception as exc:  # pragma: no cover — last-resort safety net for the demo
            last_error = f"Unexpected LLM error: {exc}"
            break

    return _fallback(findings, last_error)
