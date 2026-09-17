import React, { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem("financeos_user");
    return raw ? JSON.parse(raw) : null;
  });

  async function login(email, password) {
    const data = await api.login(email, password);
    localStorage.setItem("financeos_token", data.access_token);
    const u = { email: data.email, role: data.role };
    localStorage.setItem("financeos_user", JSON.stringify(u));
    setUser(u);
    return u;
  }

  function logout() {
    localStorage.removeItem("financeos_token");
    localStorage.removeItem("financeos_user");
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
