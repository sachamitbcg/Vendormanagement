# Design decisions & trade-offs

Five decisions that shaped this build, each with what I traded away.

**1. Rules first, LLM second.** A deterministic engine (`screening.py`) normalises tax IDs
and bank accounts and finds exact/partial duplicates *before* the LLM runs; those findings
are handed to Claude as ground truth. The model does judgement and wording (tier, rationale,
reviewer checklist), not fact-finding. *Why:* duplicate detection must be 100% reproducible
and auditable — a Finance control can't rely on a probabilistic model to notice that two bank
accounts match. *Trade-off:* matching is exact-on-normalised-fields; fuzzy name matching
("Ltd" vs "Limited") is out of scope.

**2. AI degrades gracefully, never auto-approves.** The gateway requests API-enforced JSON
(`output_config.format`), parses and stores it, retries once, and on any failure (no key,
timeout, bad JSON) falls back to a rule-derived tier with a UI banner. Vendors are always
created `pending`; approval is a separate, reviewer-only action. *Why:* the brief requires
graceful failure and AI-as-assistant (3.2, 6.2, 6.4) — a demo that survives a dropped network
beats one that crashes. *Trade-off:* the fallback rationale is templated, so it reads less
naturally than Claude's.

**3. Prompt externalised.** The system + user prompt and the JSON response schema live in
`prompts/vendor_screening.md`, parsed at startup; route handlers hold no prompt text. *Why:*
design 6.3 — prompts should be externalised, structured, and tunable without touching code.
*Trade-off:* a little parsing code and a light file convention rather than a template engine.

**4. Everything auditable.** `audit.py` logs every AI decision and every human override; the
dashboard derives AI-vs-human override rate from that log. *Why:* "if you cannot measure
override rate, you cannot improve the model" (6.2), and it is the honest record of who decided
what. *Trade-off:* `audit_log.entity_id` is a polymorphic pointer at a vendor, not a formal
foreign key — flexible for other entity types later, but no DB-level integrity on that column.

**5. Schema scoped to Process 3.** Only `users`, `vendors`, and `audit_log` exist, via
Alembic. The brief's other-process tables (`invoices`, `purchase_orders`, `budget_actuals`)
are intentionally omitted. *Why:* scope discipline (6.5) — every table in the repo is actually
exercised, which reads more honestly than dead scaffolding. *Trade-off:* the schema no longer
mirrors the brief's full six-table list; each is a one-migration add when those processes are
built.

**Not built (deliberately):** sanctions/watchlist screening (Appendix A supplies no watchlist
to screen against, so it would be a stub — the reviewer checklist prompts a human instead);
fuzzy name matching (keeps the duplicate signal deterministic); SSO, mobile, multi-tenancy,
CI/CD, and production-grade security (out of scope per 6.5).

**With more time:** fuzzy name matching with a confidence score feeding the LLM; an eval
harness comparing AI tier vs final human tier over time; ABN-checksum and BSB-format
validation; unit tests for `screening.py` (the Appendix A4 duplicates are a ready fixture set).
