import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  function quickFill(role) {
    setEmail(`${role}@financeos.demo`);
    setPassword("demo1234");
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="brand-lg">
          FinanceOS<span className="brand-sub"> · Vendor Screener</span>
        </div>
        <p className="muted">Sign in to screen and onboard vendors.</p>

        <form onSubmit={submit}>
          <label>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@financeos.demo"
            required
          />
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="form-error">{error}</div>}
          <button className="primary" disabled={busy} type="submit">
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="demo-accounts">
          <div className="muted small">Demo accounts (password: demo1234)</div>
          <button className="link-btn" onClick={() => quickFill("analyst")}>
            Use analyst
          </button>
          <button className="link-btn" onClick={() => quickFill("reviewer")}>
            Use reviewer
          </button>
        </div>
      </div>
    </div>
  );
}
