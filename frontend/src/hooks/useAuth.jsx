import { useState, useEffect, createContext, useContext } from 'react';
import { getMe, login as apiLogin, register as apiRegister, logout as apiLogout } from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Run once on mount
  useEffect(() => {
    checkAuth();
  }, []);

  // ── FIX: when backend redirects to /dashboard?login=success after Google OAuth,
  //         force a fresh /api/auth/me call so we pick up the new session cookie
  //         and then clean the URL so it doesn't loop on refresh.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('login') === 'success') {
      checkAuth().then(() => {
        params.delete('login');
        const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
        window.history.replaceState({}, '', clean);
      });
    }
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
