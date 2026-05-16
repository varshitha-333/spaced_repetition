import { useState, useEffect, createContext, useContext, useCallback } from 'react';
import {
  getMe, login as apiLogin, register as apiRegister, logout as apiLogout,
  getToken, setToken, clearToken,
} from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }
    try {
      const res = await getMe();
      setUser(res.data.user);
      return res.data.user;
    } catch {
      clearToken();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  // refreshUser is exposed so pages (Drive connect / Profile / Payment) can
  // force a fresh /me after backend state changes — fixes the
  // "Drive shows not connected even after connecting" bug.
  const refreshUser = useCallback(async () => {
    try {
      const res = await getMe();
      setUser(res.data.user);
      return res.data.user;
    } catch {
      return null;
    }
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get('token');
    const errorParam = params.get('error');

    if (urlToken) {
      setToken(urlToken);
      params.delete('token');
      const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
      window.history.replaceState({}, '', clean);
      checkAuth();
    } else if (errorParam) {
      params.delete('error');
      const clean = window.location.pathname + (params.toString() ? `?${params}` : '');
      window.history.replaceState({}, '', clean);
      if (errorParam === 'google_not_registered') window.__googleAuthError = 'not_registered';
      setLoading(false);
    } else {
      checkAuth();
    }
  }, [checkAuth]);

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
    <AuthContext.Provider value={{ user, loading, login, register, logout, checkAuth, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
};
