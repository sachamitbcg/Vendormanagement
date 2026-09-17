import { useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import RiskBadge from "../components/RiskBadge.jsx";

const BLANK = { name: "", abn: "", bank_account: "", category: "", contact: "" };

// Demo presets that exercise the seeded edge cases (Appendix A4).
const PRESETS = {
  clean: {
    name: "Northwind Advisory",
    abn: "12 000 111 222",
    bank_account: "BSB 062-000 / 90001111",
    category: "Consulting",
    contact: "ap@northwind.example.com",
  },
  exact: {
    name: "Acme Consulting (renewal)",
    abn: "12 345 678 901",
    bank_account: "BSB 062-000 / 12345678",
    category: "Consulting",
    contact: "ap@acme.example.com",
  },
  partial: {
    name: "Global Print — new account",
    abn: "98 765 432 100",
    bank_account: "BSB 999-999 / 55550000",
    category: "Supplies",
    contact: "ap@globalprint.example.com",
  },
  incomplete: {
    name: "Quickship Couriers",
    abn: "",
    bank_account: "BSB 083-004 / 22119988",
    category: "",
    contact: "",
  },
};

export default function Onboard() {
  const { user } = useAuth();
  const isReviewer = user?.role === "reviewer";

  const [form, setForm] = useState(BLANK);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null); // {vendor, findings, assessment}
  const [savingAction, setSavingAction] = useState("");

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    setResult(null);
    try {
      const res = await api.submitVendor(form);
      setResult(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function applyOverride(payload) {
    if (!result) return;
    setSavingAction(JSON.stringify(payload));
    try {
      const updated = await api.overrideVendor(result.vendor.id, payload);
      setResult((r) => ({ ...r, vendor: updated }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingAction("");
    }
  }

  const v = result?.vendor;
  const a = result?.assessment;
  const f = result?.findings;

  return (
    <div className="grid-2">
      {/* ---- Form ---- */}
      <section className="card">
        <h2>Onboard a vendor</h2>
        <p className="muted small">
          Submit a new vendor. It is checked against the existing vendor master for
          duplicates, then an AI assistant recommends a risk tier — a reviewer always has
          the final say.
        </p>

        <div className="presets">
          <span className="muted small">Try:</span>
          <button className="chip" onClick={() => setForm(PRESETS.clean)}>Clean vendor</button>
          <button className="chip" onClick={() => setForm(PRESETS.exact)}>Exact duplicate</button>
          <button className="chip" onClick={() => setForm(PRESETS.partial)}>Partial duplicate</button>
          <button className="chip" onClick={() => setForm(PRESETS.incomplete)}>Incomplete</button>
          <button className="chip ghost" onClick={() => setForm(BLANK)}>Clear</button>
        </div>

        <form onSubmit={submit}>
          <label>Vendor name *</label>
          <input value={form.name} onChange={(e) => update("name", e.target.value)} required />

          <label>Tax ID / ABN</label>
          <input value={form.abn} onChange={(e) => update("abn", e.target.value)} placeholder="12 345 678 901" />

          <label>Bank account</label>
          <input
            value={form.bank_account}
            onChange={(e) => update("bank_account", e.target.value)}
            placeholder="BSB 062-000 / 12345678"
          />

          <label>Category</label>
          <input value={form.category} onChange={(e) => update("category", e.target.value)} placeholder="Consulting" />

          <label>Contact</label>
          <input value={form.contact} onChange={(e) => update("contact", e.target.value)} placeholder="ap@vendor.com" />

          {error && <div className="form-error">{error}</div>}
          <button className="primary" type="submit" disabled={busy}>
            {busy ? "Screening…" : "Screen & submit"}
          </button>
        </form>
      </section>

      {/* ---- Result ---- */}
      <section className="card">
        <h2>Screening result</h2>

        {busy && (
          <div className="loading">
            <div className="spinner" />
            <div>Running duplicate checks and asking the AI assistant…</div>
          </div>
        )}

        {!busy && !result && (
          <div className="empty">
            No vendor screened yet. Fill in the form (or pick a preset) and select
            <strong> Screen &amp; submit</strong>.
          </div>
        )}

        {!busy && result && (
          <div className="result">
            {a.source === "fallback" && (
              <div className="banner banner-warn small">
                AI assistant unavailable — showing the rule-based recommendation.
                {a.llm_error ? ` (${a.llm_error})` : ""}
              </div>
            )}

            <div className="result-head">
              <div>
                <div className="muted small">AI recommended tier</div>
                <div className="tier-row">
                  <RiskBadge tier={v.risk_tier} />
                  <span className="src-pill">{a.source === "llm" ? "Claude" : "rules"}</span>
                </div>
              </div>
              <div className="result-vendor">
                <div className="vendor-name">{v.name}</div>
                <div className="muted small">Vendor #{v.id} · status: {v.onboarding_status}</div>
              </div>
            </div>

            <p className="rationale">{v.ai_rationale}</p>

            {/* Duplicate findings (rule engine) */}
            <div className="subsection">
              <div className="subhead">Duplicate check</div>
              {f.duplicates.length === 0 ? (
                <div className="muted small">No duplicate match in the vendor master.</div>
              ) : (
                <ul className="findings">
                  {f.duplicates.map((d, i) => (
                    <li key={i}>
                      <span className={`tag tag-${d.match_type}`}>{d.match_type}</span>{" "}
                      matches <strong>{d.vendor_name}</strong> on {d.matched_on.join(", ")}
                      {d.differs_on.length > 0 && <> · differs on {d.differs_on.join(", ")}</>}
                    </li>
                  ))}
                </ul>
              )}
              {!f.completeness_ok && (
                <div className="muted small">
                  Missing required fields: {f.missing_fields.join(", ")}
                </div>
              )}
            </div>

            {a.anomalies.length > 0 && (
              <div className="subsection">
                <div className="subhead">Anomalies flagged</div>
                <ul className="findings">
                  {a.anomalies.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              </div>
            )}

            {v.verify_checklist.length > 0 && (
              <div className="subsection">
                <div className="subhead">What the reviewer should verify</div>
                <ul className="checklist">
                  {v.verify_checklist.map((x, i) => <li key={i}>{x}</li>)}
                </ul>
              </div>
            )}

            {/* Reviewer actions */}
            <div className="subsection review-box">
              <div className="subhead">Reviewer decision</div>
              {v.human_override && (
                <div className="muted small">
                  Overridden to <strong>{v.human_override}</strong> (effective tier:{" "}
                  {v.effective_tier}).
                </div>
              )}
              {!isReviewer ? (
                <div className="muted small">
                  Sign in as a <strong>reviewer</strong> to override the tier or approve /
                  reject this vendor.
                </div>
              ) : (
                <>
                  <div className="btn-row">
                    <span className="muted small">Override tier:</span>
                    {["Low", "Medium", "High"].map((t) => (
                      <button
                        key={t}
                        className="chip"
                        disabled={!!savingAction}
                        onClick={() => applyOverride({ risk_tier: t })}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                  <div className="btn-row">
                    <button
                      className="btn-approve"
                      disabled={!!savingAction || v.onboarding_status === "approved"}
                      onClick={() => applyOverride({ onboarding_status: "approved" })}
                    >
                      Approve onboarding
                    </button>
                    <button
                      className="btn-reject"
                      disabled={!!savingAction || v.onboarding_status === "rejected"}
                      onClick={() => applyOverride({ onboarding_status: "rejected" })}
                    >
                      Reject
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
