# Design decisions & trade-offs

Five decisions that shaped this build, and what I traded away for each.

## 1. Rules first, LLM second — the model never invents a duplicate

Duplicate detection is done by a deterministic engine (`screening.py`) that normalises tax
IDs and bank accounts and compares them against the vendor master **before** the LLM is
called. The rule findings are then handed to Claude as ground truth. The model's job is
judgement and communication (tier + rationale + reviewer checklist), not fact-finding.

*Why:* duplicate detection is exactly the kind of thing that must be 100% reproducible and
auditable — a Finance control can't depend on a probabilistic model to notice that two bank
accounts match. It also keeps the exact-vs-partial logic testable in isolation.
*Trade-off:* the rules are intentionally simple (exact-match on normalised fields). Fuzzy
name matching ("Acme Ltd" vs "Acme Limited") is out of scope; the model can still comment on
near-matches it's shown, but the hard duplicate signal is rule-based.

## 2. The LLM layer degrades gracefully and never auto-approves

The gateway requests **structured JSON** (via `output_config.format`), parses and stores it,
retries once, and on any failure (no key, timeout, rate-limit, bad JSON) falls back to a
rule-derived tier and surfaces the error to the UI as a banner. New vendors are always
created as `pending`; approval is a separate, reviewer-only action.

*Why:* the brief is explicit — handle LLM failure gracefully, show a fallback state, and
treat AI as an assistant, not an oracle (design 3.2, 6.2, 6.4). A demo that survives a
dropped network or a missing key is worth more than one that crashes.
*Trade-off:* the fallback rationale is templated rather than generated, so it reads less
naturally than Claude's output — an acceptable price for always-on reliability.

## 3. Prompt is externalised and version-controlled

The full system + user prompt and the JSON response schema live in
`prompts/vendor_screening.md`, parsed at startup. Route handlers contain no prompt text.

*Why:* design 6.3 — prompts should be externalised, structured, and iterable. It also means
the prompt can be reviewed and tuned by a non-engineer, and the iteration history is captured
in one place (useful for the "explain one prompt" part of the interview).
*Trade-off:* a small amount of parsing code, and the prompt format is a light convention
rather than a formal template engine.

## 4. Everything is auditable; the dashboard measures override rate

`audit.py` writes a row for every AI screening and every human override/approval/rejection.
The dashboard derives AI-vs-human override rate directly from that log.

*Why:* "if you cannot measure override rate, you cannot improve the model" (design 6.2). The
eval log is also the honest record of who decided what — a real Finance control requirement.
*Trade-off:* `audit_log.entity_id` is a polymorphic pointer at `vendors.id`, not a formal
foreign key, so it can reference other entity types later without a schema change — at the
cost of DB-level referential integrity on that column.

## 5. Schema matches the brief; scope is deliberately narrowed to Process 3

All six tables from section 3.3 are created via Alembic, but only `users`, `vendors`, and
`audit_log` are exercised. `invoices`, `purchase_orders`, and `budget_actuals` are
schema-only.

*Why:* scope discipline (design 6.5) — one process built well beats three half-built. Having
the full schema present keeps the door open and matches the brief exactly.
*Trade-off:* those three tables are dead weight in this POC; that's the intended signal, not
an oversight.

---

## What I did **not** build, and why

- **Sanctions / watchlist screening.** The brief names it, but Appendix A supplies no
  watchlist to screen against, so any implementation would be a stub. Left out rather than
  faked; the reviewer checklist prompts the human to run it.
- **Fuzzy name matching.** Deferred to keep the duplicate signal deterministic (see #1).
- **SSO, mobile layouts, multi-tenancy, CI/CD, production-grade security.** Explicitly out of
  scope per the brief (design 6.5).
- **Streaming LLM responses / prompt versioning UI.** Encouraged extras; skipped in favour of
  reliability and a clean human-in-the-loop flow. The prompt file already records its own
  iteration history.

## If I had more time

- Fuzzy name matching with a confidence score feeding the LLM.
- A proper eval harness: replay historical decisions, compare AI tier vs final human tier,
  track precision/recall per tier over time.
- Per-field validation of ABN checksums and BSB formats.
- Unit tests around `screening.py` edge cases (the Appendix A4 duplicates make a ready-made
  fixture set).
