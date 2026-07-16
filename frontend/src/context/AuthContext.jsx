import { createContext, useContext, useEffect, useState, useCallback } from "react";
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

  const login = async (email, password) => {
    const u = await authLogin(email, password);
    setUser(u);
    return u;
  };

  const register = async (email, password, officeName) => {
    const u = await authRegister(email, password, officeName);
    setUser(u);
    return u;
  };

  const logout = async () => {
    try {
      await authLogout();
    } catch {
      /* ignore */
    }
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
