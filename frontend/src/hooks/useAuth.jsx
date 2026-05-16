import { useState, useEffect, createContext, useContext } from 'react';
import { getMe, login as apiLogin, register as apiRegister, logout as apiLogout } from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initial auth check on mount
  useEffect(() => {
    checkAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle Google OAuth redirect:  /dashboard?login=success
  // After Google login, backend redirects here. We force /me to load the new session
  // and then clean the URL.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('login') === 'success') {
      console.log('[AUTH] Google callback redirect detected, refreshing session...');
      checkAuth().then(() => {
        params.delete('login');
        const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
        window.history.replaceState({}, '', clean);
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAuth = async () => {
    try {
      const res = await getMe();
      console.log('[AUTH] /me OK:', res.data.user);
      setUser(res.data.user);
      return res.data.user;
    } catch (err) {
      console.log('[AUTH] /me failed (status', err.response?.status, ') — user not logged in');
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    const res = await apiLogin(username, password);
    console.log('[AUTH] login response:', res.data);
    setUser(res.data.user);
    // 🔧 Re-verify session immediately so we know the cookie was actually stored.
    // If this fails right after a 200 login, you have a cross-site cookie problem.
    setTimeout(async () => {
      const me = await checkAuth();
      if (!me) {
        console.error('[AUTH] ❌ Login succeeded but /me still 401 — session cookie was not stored. '
          + 'This means: (a) backend missing ProxyFix, (b) browser blocking 3rd-party cookies, '
          + 'or (c) frontend not using HTTPS. Check Network tab → Login response → Set-Cookie header.');
      }
    }, 100);
    return res;
  };

  const register = async (username, password, email) => {
    const res = await apiRegister(username, password, email);
    if (res?.data?.user) setUser(res.data.user);
    setTimeout(() => checkAuth(), 100);
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
