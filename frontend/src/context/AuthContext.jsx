import { createContext, useContext, useEffect, useState, useCallback, useMemo } from "react";
import { authMe, authLogin, authRegister, authLogout } from "@/lib/api";

// user states: undefined (checking), user object (authenticated), null (not authenticated)
const AuthContext = createContext({
  user: undefined,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  refresh: async () => {},
});

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined);

  const refresh = useCallback(async () => {
    try {
      const me = await authMe();
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const login = useCallback(async (email, password, remember = false) => {
    const u = await authLogin(email, password, remember);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (email, password, officeName) => {
    const u = await authRegister(email, password, officeName);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    try {
      await authLogout();
    } catch {
      /* ignore */
    }
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, login, register, logout, refresh }),
    [user, login, register, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
