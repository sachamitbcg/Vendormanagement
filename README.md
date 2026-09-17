# FinanceOS — Vendor Risk & Onboarding Screener

Process 3 of the FinanceOS technical assessment. A working web app that screens new
vendors against the existing vendor master, uses an LLM (Anthropic Claude) to recommend a
risk tier with a plain-English rationale, and keeps a human reviewer in control of every
decision.

- **Frontend:** React (Vite)
- **Backend:** FastAPI (Python)
- **Database:** SQLite with Alembic migrations
- **LLM:** Anthropic Claude (`claude-opus-4-8`), with a rule-based fallback
- **Auth:** email/password → JWT (no SSO)

The solution architecture is in [`docs/architecture.png`](docs/architecture.png); key
design trade-offs are in [`docs/design-decisions.md`](docs/design-decisions.md); the LLM
prompt lives in [`prompts/vendor_screening.md`](prompts/vendor_screening.md).

---

## What it does

1. An **analyst** signs in and submits a new vendor (name, tax ID/ABN, bank account,
   category, contact).
2. A deterministic **screening engine** checks the vendor master for **exact** duplicates
   (same tax ID *and* bank) and **partial** duplicates (one matches, one differs), and
   validates completeness.
3. The **LLM gateway** sends those findings plus the form to Claude and gets back a
   structured JSON assessment: risk tier (Low/Medium/High), one-sentence rationale, list of
   anomalies, and a reviewer checklist. The output is **parsed and stored**.
4. A **reviewer** can override the tier and approve / reject onboarding. Every AI decision
   and every human override is written to an **audit / eval log**.
5. The **vendor master** view shows all vendors, their (effective) risk tier and status,
   plus dashboard KPIs and the eval log (including AI-vs-human override rate).

If no `ANTHROPIC_API_KEY` is set — or Claude times out / errors — the app **still works**:
it falls back to the rule-based tier and shows an "AI unavailable" banner. It never
auto-approves.

---

## Prerequisites

- Python 3.11+ (tested on 3.13)
- Node.js 18+ (tested on Node 24)

---

## 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:  .venv\Scripts\Activate.ps1
# Windows Git Bash:    source .venv/Scripts/activate
# macOS / Linux:       source .venv/bin/activate
pip install -r requirements.txt
```

Create the env file (copy the template at the repo root):

```bash
cp ../.env.example .env
```

Edit `backend/.env` and set `ANTHROPIC_API_KEY` to enable live Claude calls. **Leaving it
blank is fine** — the app runs in rule-only fallback mode.

Create the schema (migrations):

```bash
alembic upgrade head        # creates all six tables
```

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

**Seeding is automatic.** On startup the app loads the 2 demo users and the 25-row
vendor master (Appendix A4) if the database is empty, so the data is always present
whenever you launch — no manual step. (You can still run `python -m app.seed`
explicitly if you prefer.) The seed is idempotent: it never duplicates rows and never
touches data you've added during a demo.

- API docs: <http://localhost:8000/docs>
- Health / LLM-mode probe: <http://localhost:8000/api/health>

### Dropping and recreating the schema cleanly

```bash
alembic downgrade base && alembic upgrade head    # or just delete financeos.db
# next launch re-seeds automatically; or run `python -m app.seed` now
```

## 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

---

## Demo credentials

| Role     | Email                      | Password   | Can do                          |
| -------- | -------------------------- | ---------- | ------------------------------- |
| Analyst  | `analyst@financeos.demo`   | `demo1234` | Submit & screen vendors         |
| Reviewer | `reviewer@financeos.demo`  | `demo1234` | Everything + override / approve |

The login screen has one-click buttons to fill each account.

---

## Suggested demo path

1. Sign in as the **analyst**. On *Onboard a vendor*, click the **Exact duplicate** preset
   and *Screen & submit* → tier **High**, flags the duplicate of *Acme Consulting Ltd*.
2. Try the **Partial duplicate** preset → tier **Medium** (same ABN, different bank).
3. Try the **Clean vendor** and **Incomplete** presets to see Low / Medium.
4. Sign out, sign in as the **reviewer**, screen a vendor, then **override** the tier and
   **approve** it.
5. Go to **Vendor master** to see the KPIs, the full vendor list, and the **eval log** with
   the AI decisions and your override.

---

## Project layout

```
Vendormanagement/
├─ README.md
├─ .env.example
├─ docs/
│  ├─ architecture.png          # solution architecture (also .svg + .drawio)
│  └─ design-decisions.md
├─ prompts/
│  └─ vendor_screening.md        # externalised system + user prompt + JSON schema
├─ backend/
│  ├─ requirements.txt
│  ├─ alembic.ini / alembic/     # migrations
│  └─ app/
│     ├─ main.py                 # FastAPI app
│     ├─ models.py               # all six tables (3 exercised, 3 schema-only)
│     ├─ screening.py            # deterministic duplicate / completeness engine
│     ├─ llm_gateway.py          # Claude call + parse + retry + fallback
│     ├─ audit.py                # logs every AI decision & human override
│     ├─ routers/                # auth, vendors, dashboard
│     └─ seed.py                 # demo users + Appendix A4 vendor master
└─ frontend/                     # React (Vite): login, onboard, vendor master
```

## Notes for the reviewer

- **No key needed to try it.** Rule-only fallback covers the full flow; add a key for live
  Claude output.
- The three non-vendor tables (`invoices`, `purchase_orders`, `budget_actuals`) exist so the
  schema matches the brief exactly, but are **not exercised** by this POC — a deliberate,
  documented scope choice (see `docs/design-decisions.md`).
- Ports: backend `8000`, frontend `5173`. If you change the backend port, set
  `VITE_API_BASE` for the frontend.
