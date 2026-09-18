import React, { useEffect, useState } from "react";
import { api } from "../api";
import { useAuth } from "../auth.jsx";
import RiskBadge from "../components/RiskBadge.jsx";

export default function VendorMaster() {
  const { user } = useAuth();
  const isReviewer = user?.role === "reviewer";

  const [vendors, setVendors] = useState([]);
  const [stats, setStats] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const [selected, setSelected] = useState(null); // vendor open in the review drawer
  const [saving, setSaving] = useState(false);
  const [onlyPending, setOnlyPending] = useState(false);

  async function refresh(keepSelectedId) {
    setLoading(true);
    setError("");
    try {
      const [v, s, a] = await Promise.all([api.listVendors(), api.stats(), api.audit()]);
      setVendors(v);
      setStats(s);
      setAudit(a);
      if (keepSelectedId) {
        setSelected(v.find((x) => x.id === keepSelectedId) || null);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function act(payload) {
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      const updated = await api.overrideVendor(selected.id, payload);
      setSelected(updated);
      await refresh(updated.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  const rows = onlyPending
    ? vendors.filter((v) => v.onboarding_status === "pending")
    : vendors;

  return (
    <div className="stack">
      {error && <div className="banner banner-warn">{error}</div>}

      {/* KPI tiles */}
      <section className="kpis">
        <div className="kpi">
          <div className="kpi-value">{stats?.total_vendors ?? "—"}</div>
          <div className="kpi-label">Vendors on file</div>
        </div>
        <div className="kpi">
          <div className="kpi-value">{stats?.ai_decisions ?? "—"}</div>
          <div className="kpi-label">AI screenings run</div>
        </div>
        <div className="kpi">
          <div className="kpi-value">{stats?.human_overrides ?? "—"}</div>
          <div className="kpi-label">Human overrides</div>
        </div>
        <div className="kpi">
          <div className="kpi-value">
            {stats ? `${Math.round(stats.override_rate * 100)}%` : "—"}
          </div>
          <div className="kpi-label">Override rate</div>
        </div>
        <div className="kpi">
          <div className="kpi-value">{stats?.by_status?.pending ?? "—"}</div>
          <div className="kpi-label">Pending review</div>
        </div>
      </section>

      {/* Vendor table */}
      <section className="card">
        <div className="card-head">
          <h2>Vendor master</h2>
          <div className="btn-row" style={{ marginTop: 0 }}>
            <label className="muted small" style={{ display: "flex", gap: 6, alignItems: "center", margin: 0 }}>
              <input
                type="checkbox"
                style={{ width: "auto" }}
                checked={onlyPending}
                onChange={(e) => setOnlyPending(e.target.checked)}
              />
              Pending only
            </label>
            <button className="link-btn" onClick={() => refresh()}>Refresh</button>
          </div>
        </div>
        <p className="muted small">
          {isReviewer
            ? "Click any vendor to review its screening and approve, reject, or override the tier."
            : "Click any vendor to view its screening detail. (Sign in as a reviewer to take action.)"}
        </p>
        {loading ? (
          <div className="loading"><div className="spinner" /> Loading…</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Tax ID / ABN</th>
                  <th>Risk tier</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((v) => (
                  <tr key={v.id} className="clickable" onClick={() => setSelected(v)}>
                    <td className="muted">{v.id}</td>
                    <td>{v.name}</td>
                    <td>{v.category || "—"}</td>
                    <td className="mono">{v.abn || "—"}</td>
                    <td>
                      <RiskBadge tier={v.effective_tier} />
                      {v.human_override && <span className="src-pill">overridden</span>}
                    </td>
                    <td>
                      <span className={`status status-${v.onboarding_status}`}>
                        {v.onboarding_status}
                      </span>
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr><td colSpan={6} className="empty">
                    {vendors.length === 0
                      ? "No vendors yet — submit one from “Onboard a vendor”."
                      : "No vendors match this filter."}
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Eval log */}
      <section className="card">
        <h2>Eval log — AI decisions &amp; human overrides</h2>
        <p className="muted small">
          Every AI screening and every human override is recorded here. This is what lets
          us measure override rate and, over time, improve the model.
        </p>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>When</th>
                <th>User</th>
                <th>Action</th>
                <th>Vendor</th>
                <th>From → To</th>
              </tr>
            </thead>
            <tbody>
              {audit.map((e) => (
                <tr key={e.id}>
                  <td className="muted small">{new Date(e.timestamp).toLocaleString()}</td>
                  <td className="small">{e.user_email || "—"}</td>
                  <td><span className={`tag tag-${e.action}`}>{e.action}</span></td>
                  <td className="muted">#{e.entity_id}</td>
                  <td className="small">
                    {e.old_value ? `${e.old_value} → ` : ""}
                    {e.new_value || "—"}
                  </td>
                </tr>
              ))}
              {audit.length === 0 && (
                <tr><td colSpan={5} className="empty">No activity logged yet.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* ---- Review drawer ---- */}
      {selected && (
        <div className="modal-overlay" onClick={() => !saving && setSelected(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="vendor-name">{selected.name}</div>
                <div className="muted small">
                  Vendor #{selected.id} · {selected.category || "no category"}
                </div>
              </div>
              <button className="link-btn" onClick={() => setSelected(null)}>Close ✕</button>
            </div>

            <div className="modal-body">
              <div className="kv">
                <div><span className="muted small">Tax ID / ABN</span><div className="mono">{selected.abn || "—"}</div></div>
                <div><span className="muted small">Bank account</span><div className="mono">{selected.bank_account || "—"}</div></div>
                <div><span className="muted small">Contact</span><div>{selected.contact || "—"}</div></div>
                <div><span className="muted small">Status</span><div><span className={`status status-${selected.onboarding_status}`}>{selected.onboarding_status}</span></div></div>
              </div>

              <div className="subsection">
                <div className="subhead">Risk assessment</div>
                <div className="tier-row">
                  <span className="muted small" style={{ marginRight: 8 }}>Effective tier:</span>
                  <RiskBadge tier={selected.effective_tier} />
                  {selected.risk_tier && (
                    <span className="src-pill">
                      AI: {selected.risk_tier}
                      {selected.ai_source ? ` (${selected.ai_source === "llm" ? "Claude" : "rules"})` : ""}
                    </span>
                  )}
                  {selected.human_override && <span className="src-pill">overridden → {selected.human_override}</span>}
                </div>
                {selected.ai_rationale && <p className="rationale">{selected.ai_rationale}</p>}
                {!selected.risk_tier && (
                  <div className="muted small">
                    This is a pre-existing vendor from the master — it predates AI screening.
                  </div>
                )}
              </div>

              {selected.anomalies?.length > 0 && (
                <div className="subsection">
                  <div className="subhead">Anomalies flagged</div>
                  <ul className="findings">{selected.anomalies.map((x, i) => <li key={i}>{x}</li>)}</ul>
                </div>
              )}

              {selected.verify_checklist?.length > 0 && (
                <div className="subsection">
                  <div className="subhead">What to verify</div>
                  <ul className="checklist">{selected.verify_checklist.map((x, i) => <li key={i}>{x}</li>)}</ul>
                </div>
              )}

              <div className="subsection review-box">
                <div className="subhead">Reviewer decision</div>
                {!isReviewer ? (
                  <div className="muted small">Sign in as a <strong>reviewer</strong> to override or approve.</div>
                ) : (
                  <>
                    <div className="btn-row">
                      <span className="muted small">Override tier:</span>
                      {["Low", "Medium", "High"].map((t) => (
                        <button
                          key={t}
                          className={`chip ${selected.effective_tier === t ? "chip-active" : ""}`}
                          disabled={saving}
                          onClick={() => act({ risk_tier: t })}
                        >
                          {t}
                        </button>
                      ))}
                    </div>
                    <div className="btn-row">
                      <button
                        className="btn-approve"
                        disabled={saving || selected.onboarding_status === "approved"}
                        onClick={() => act({ onboarding_status: "approved" })}
                      >
                        Approve onboarding
                      </button>
                      <button
                        className="btn-reject"
                        disabled={saving || selected.onboarding_status === "rejected"}
                        onClick={() => act({ onboarding_status: "rejected" })}
                      >
                        Reject
                      </button>
                      {selected.onboarding_status !== "pending" && (
                        <button className="chip ghost" disabled={saving} onClick={() => act({ onboarding_status: "pending" })}>
                          Reset to pending
                        </button>
                      )}
                    </div>
                    {saving && <div className="muted small">Saving…</div>}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
