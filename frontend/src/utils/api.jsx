import axios from 'axios';

// In production (Vercel): set VITE_API_URL = https://spaced-repetition-59xo.onrender.com
// In dev (localhost):     leave empty — Vite proxies /api/* to localhost:5000
const API_BASE = import.meta.env.VITE_API_URL || '';

console.log('[API] baseURL =', API_BASE || '(same-origin / proxy)');

// ── Token storage helpers ──
// JWT is stored in localStorage and sent as Authorization: Bearer <token>
// This completely bypasses cross-site cookie restrictions.
export const getToken  = () => localStorage.getItem('auth_token');
export const setToken  = (t) => localStorage.setItem('auth_token', t);
export const clearToken = () => localStorage.removeItem('auth_token');

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,          // cookies no longer needed
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Attach JWT to every outgoing request ──
api.interceptors.request.use((cfg) => {
  const token = getToken();
  if (token) {
    cfg.headers['Authorization'] = `Bearer ${token}`;
  }
  console.log(`[API →] ${cfg.method?.toUpperCase()} ${cfg.url}  hasToken=${!!token}`);
  return cfg;
});

// ── Debug response interceptor ──
api.interceptors.response.use(
  (res) => {
    console.log(`[API ←] ${res.status} ${res.config.url}`);
    return res;
  },
  (err) => {
    const status = err.response?.status;
    const url = err.config?.url;
    console.warn(`[API ✗] ${status} ${url}`, err.response?.data);
    return Promise.reject(err);
  }
);

// ── Auth ──
export const login = async (username, password) => {
  const res = await api.post('/api/auth/login', { username, password });
  if (res.data?.token) {
    setToken(res.data.token);
    console.log('[API] Token stored after login');
  }
  return res;
};

export const register = async (username, password, email) => {
  const res = await api.post('/api/auth/register', { username, password, email });
  if (res.data?.token) {
    setToken(res.data.token);
    console.log('[API] Token stored after register');
  }
  return res;
};

export const logout = () => {
  clearToken();
  console.log('[API] Token cleared on logout');
  // Tell the backend too (best-effort; JWT is stateless so this is informational only)
  return api.post('/api/auth/logout').catch(() => {});
};

export const getMe = () => api.get('/api/auth/me');

// Debug helper — call from console: window.__healthCheck()
export const healthCheck = () => api.get('/api/health');
if (typeof window !== 'undefined') {
  window.__healthCheck = () => healthCheck().then(r => console.log('HEALTH:', r.data));
}

// mode = 'login' | 'register'
export const getGoogleAuthUrl = (mode = 'login') =>
  api.get('/api/auth/google', { params: { mode } });

// ── Drive ──
export const connectDrive = () => api.get('/api/drive/connect');
export const disconnectDrive = () => api.post('/api/drive/disconnect');

// ── Upload ──
export const uploadPreview = (formData) =>
  api.post('/api/upload/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const uploadSave = (data) => api.post('/api/upload/save', data);

// ── Revisions ──
export const getTodayRevisions    = () => api.get('/api/revisions/today');
export const getOverdueRevisions  = () => api.get('/api/revisions/overdue');
export const getCompletedRevisions = () => api.get('/api/revisions/completed');
export const getUpcomingRevisions  = () => api.get('/api/revisions/upcoming');
export const getRevisionStats      = () => api.get('/api/revisions/stats');

export const completeRevision = (id) => api.post(`/api/revisions/${id}/complete`);
export const postponeRevision = (id) => api.post(`/api/revisions/${id}/postpone`);
export const skipRevision     = (id) => api.post(`/api/revisions/${id}/skip`);

// ── Learnings ──
export const getLearnings = () => api.get('/api/learnings');

export default api;