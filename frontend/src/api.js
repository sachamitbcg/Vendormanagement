// Thin API client. Reads the JWT from localStorage and attaches it to every call.
const BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function token() {
  return localStorage.getItem("financeos_token");
}

async function handle(res) {
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

function authHeaders(extra = {}) {
  const t = token();
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

export const api = {
  base: BASE,

  async login(email, password) {
    // FastAPI's OAuth2PasswordRequestForm expects form-encoded username/password.
    const body = new URLSearchParams({ username: email, password });
    const res = await fetch(`${BASE}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    return handle(res);
  },

  async health() {
    return handle(await fetch(`${BASE}/api/health`));
  },

  async submitVendor(payload) {
    const res = await fetch(`${BASE}/api/vendors`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  async listVendors() {
    return handle(await fetch(`${BASE}/api/vendors`, { headers: authHeaders() }));
  },

  async overrideVendor(id, payload) {
    const res = await fetch(`${BASE}/api/vendors/${id}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(payload),
    });
    return handle(res);
  },

  async stats() {
    return handle(await fetch(`${BASE}/api/stats`, { headers: authHeaders() }));
  },

  async audit() {
    return handle(await fetch(`${BASE}/api/audit`, { headers: authHeaders() }));
  },
};
