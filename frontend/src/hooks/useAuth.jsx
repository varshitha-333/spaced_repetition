import { useState, useEffect, createContext, useContext } from 'react';
import {
  getMe,
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  getToken,
  setToken,
  clearToken,
} from '../utils/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // ── On mount: check for a Google OAuth token in the URL first,
  //    then fall back to checking an existing stored token. ──
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');       // set by Google OAuth callback
    const errorParam = params.get('error');

    if (urlToken) {
      // Google OAuth completed — save the token and clean the URL
      console.log('[AUTH] Google OAuth token received in URL — storing...');
      setToken(urlToken);
      params.delete('token');
      const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
      window.history.replaceState({}, '', clean);
      // Now verify the token by calling /me
      checkAuth();
    } else if (errorParam) {
      console.warn('[AUTH] Google OAuth error:', errorParam);
      params.delete('error');
      const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
      window.history.replaceState({}, '', clean);
      // Surface a user-friendly message for the "not registered" case
      if (errorParam === 'google_not_registered') {
        console.warn('[AUTH] Google sign-in blocked — email not registered. User must register first.');
        // Store so Login page can pick it up and show a toast / banner
        window.__googleAuthError = 'not_registered';
      }
      setLoading(false);
    } else {
      // Normal page load — check if we already have a stored token
      checkAuth();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const checkAuth = async () => {
    // If there is no token at all, don't even bother calling the API
    if (!getToken()) {
      console.log('[AUTH] No token in storage — skipping /me call');
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const res = await getMe();
      console.log('[AUTH] /me OK:', res.data.user);
      setUser(res.data.user);
      return res.data.user;
    } catch (err) {
      const status = err.response?.status;
      console.log('[AUTH] /me failed (status', status, ') — clearing token');
      // Token is invalid or expired — remove it so user gets sent to login
      clearToken();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    // apiLogin already calls setToken internally (see api.jsx)
    const res = await apiLogin(username, password);
    console.log('[AUTH] login response:', res.data);
    setUser(res.data.user);
    return res;
  };

  const register = async (username, password, email) => {
    const res = await apiRegister(username, password, email);
    if (res?.data?.user) setUser(res.data.user);
    return res;
  };

  const logout = async () => {
    await apiLogout();   // clears token from localStorage
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