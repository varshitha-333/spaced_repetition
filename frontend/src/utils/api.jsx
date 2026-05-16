import axios from 'axios';

// In production (Vercel), set VITE_API_URL = https://spaced-repetition-59xo.onrender.com
// In dev (localhost), leave it empty and Vite proxies /api/* to localhost:5000
const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Auth ──
export const login = (username, password) =>
  api.post('/api/auth/login', { username, password });

export const register = (username, password, email) =>
  api.post('/api/auth/register', { username, password, email });

export const logout = () => api.post('/api/auth/logout');

export const getMe = () => api.get('/api/auth/me');

// mode = 'login' | 'register'  (purely informational for the backend)
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
export const getTodayRevisions = () => api.get('/api/revisions/today');
export const getOverdueRevisions = () => api.get('/api/revisions/overdue');
export const getCompletedRevisions = () => api.get('/api/revisions/completed');
export const getUpcomingRevisions = () => api.get('/api/revisions/upcoming');
export const getRevisionStats = () => api.get('/api/revisions/stats');

export const completeRevision = (id) => api.post(`/api/revisions/${id}/complete`);
export const postponeRevision = (id) => api.post(`/api/revisions/${id}/postpone`);
export const skipRevision = (id) => api.post(`/api/revisions/${id}/skip`);

// ── Learnings ──
export const getLearnings = () => api.get('/api/learnings');

export default api;
