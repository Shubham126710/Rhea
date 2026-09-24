import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { fetchCurrentUser, login as apiLogin, logout as apiLogout } from "../api/client.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const current = await fetchCurrentUser().catch(() => null);
    setUser(current);
    return current;
  }, []);

  useEffect(() => {
    // Exactly one real /auth/me call for the whole app session (a real
    // improvement over the previous static multi-page app, which
    // necessarily made one such call per full page load since each
    // route was a separate HTML document).
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(
    async (credentials) => {
      const loggedInUser = await apiLogin(credentials);
      setUser(loggedInUser);
      return loggedInUser;
    },
    [],
  );

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
