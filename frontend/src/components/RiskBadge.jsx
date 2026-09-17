const COLORS = {
  Low: { bg: "#e6f4ea", fg: "#1e7e34", border: "#bce3c6" },
  Medium: { bg: "#fff4e0", fg: "#b26a00", border: "#f5d9a6" },
  High: { bg: "#fdecea", fg: "#c62828", border: "#f5c2bd" },
};

export default function RiskBadge({ tier }) {
  const c = COLORS[tier] || { bg: "#eee", fg: "#555", border: "#ddd" };
  return (
    <span
      className="badge"
      style={{ background: c.bg, color: c.fg, borderColor: c.border }}
    >
      {tier || "—"}
    </span>
  );
}
