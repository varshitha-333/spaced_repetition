import { useState, useEffect, createContext, useContext } from 'react';
import { getMe, login as apiLogin, register as apiRegister, logout as apiLogout } from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await getMe();
      setUser(res.data.user);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const res = await apiLogin(username, password);
    setUser(res.data.user);
    return res;
  };

  const register = async (username, password, email) => {
    const res = await apiRegister(username, password, email);
    // Backend auto-logs-in on register and returns { user: {...} }
    if (res?.data?.user) setUser(res.data.user);
    return res;
  };

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
