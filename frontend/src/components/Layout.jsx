import React, { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth.jsx";

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [health, setHealth] = useState(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth(null));
  }, []);

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          FinanceOS <span className="brand-sub">· Vendor Screener</span>
        </div>
        <nav className="nav">
          <NavLink to="/" end>
            Onboard a vendor
          </NavLink>
          <NavLink to="/master">Vendor master</NavLink>
        </nav>
        <div className="user">
          <span className="role-pill">{user?.role}</span>
          <span className="email">{user?.email}</span>
          <button className="link-btn" onClick={handleLogout}>
            Sign out
          </button>
        </div>
      </header>

      {health && !health.llm_enabled && (
        <div className="banner banner-warn">
          AI assistant is running in <strong>rule-only fallback mode</strong> (no
          ANTHROPIC_API_KEY set). Screening still works — recommendations come from the
          duplicate-detection rules instead of Claude.
        </div>
      )}

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
