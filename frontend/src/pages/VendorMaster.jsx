import { useEffect, useState } from "react";
import { api } from "../api";
import RiskBadge from "../components/RiskBadge.jsx";

export default function VendorMaster() {
  const [vendors, setVendors] = useState([]);
  const [stats, setStats] = useState(null);
  const [audit, setAudit] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [v, s, a] = await Promise.all([api.listVendors(), api.stats(), api.audit()]);
      setVendors(v);
      setStats(s);
      setAudit(a);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

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
          <button className="link-btn" onClick={refresh}>Refresh</button>
        </div>
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
                {vendors.map((v) => (
                  <tr key={v.id}>
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
                  <td className="muted small">
                    {new Date(e.timestamp).toLocaleString()}
                  </td>
                  <td className="small">{e.user_email || "—"}</td>
                  <td>
                    <span className={`tag tag-${e.action}`}>{e.action}</span>
                  </td>
                  <td className="muted">#{e.entity_id}</td>
                  <td className="small">
                    {e.old_value ? `${e.old_value} → ` : ""}
                    {e.new_value || "—"}
                  </td>
                </tr>
              ))}
              {audit.length === 0 && (
                <tr>
                  <td colSpan={5} className="empty">No activity logged yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
