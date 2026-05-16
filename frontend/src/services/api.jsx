import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const getToken = () => localStorage.getItem('auth_token');
export const setToken = (t) => localStorage.setItem('auth_token', t);
export const clearToken = () => localStorage.removeItem('auth_token');

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  headers: { 'Content-Type': 'application/json' },
});

api.interceptors.request.use((cfg) => {
  const t = getToken();
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});

// ---------- Auth ----------
export const login = async (username, password) => {
  const res = await api.post('/api/auth/login', { username, password });
  if (res.data?.token) setToken(res.data.token);
  return res;
};
export const register = async (username, password, email) => {
  const res = await api.post('/api/auth/register', { username, password, email });
  if (res.data?.token) setToken(res.data.token);
  return res;
};
export const logout = () => {
  clearToken();
  return api.post('/api/auth/logout').catch(() => {});
};
export const getMe = () => api.get('/api/auth/me');

// ---------- Drive ----------
export const getGoogleAuthUrl = (mode = 'login') => api.get('/api/auth/google', { params: { mode } });
export const connectDrive = () => api.get('/api/drive/connect');
export const disconnectDrive = () => api.post('/api/drive/disconnect');

// ---------- Uploads ----------
export const uploadPreview = (fd) => api.post('/api/upload/preview', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
export const uploadSave = (d) => api.post('/api/upload/save', d);

// ---------- Revisions ----------
export const getTodayRevisions     = () => api.get('/api/revisions/today');
export const getOverdueRevisions   = () => api.get('/api/revisions/overdue');
export const getCompletedRevisions = () => api.get('/api/revisions/completed');
export const getUpcomingRevisions  = () => api.get('/api/revisions/upcoming');
export const getRevisionStats      = () => api.get('/api/revisions/stats');
export const completeRevision = (id) => api.post(`/api/revisions/${id}/complete`);
export const postponeRevision = (id) => api.post(`/api/revisions/${id}/postpone`);
export const skipRevision     = (id) => api.post(`/api/revisions/${id}/skip`);
export const getLearnings = () => api.get('/api/learnings');

// ---------- Notifications (legacy) ----------
export const getNotificationPreferences  = () => api.get('/api/notifications/preferences');
export const saveNotificationPreferences = (p) => api.put('/api/notifications/preferences', p);

// ---------- Premium ----------
export const getPremiumStatus = () => api.get('/api/premium/status');
export const redeemPremium = (payload) => api.post('/api/premium/redeem', payload);

// ---------- SMS ----------
export const enableSms = (phone, enabled = true) =>
  api.post('/api/sms/enable', { phone, enabled });
export const testSms = () => api.post('/api/sms/test');

// ---------- Reviews ----------
export const submitReview = (rating, text, name) =>
  api.post('/api/reviews', { rating, text, name });
export const getTopReviews = () => api.get('/api/reviews/top');

// ---------- Profile ----------
export const getProfile = () => api.get('/api/profile');
export const updateProfile = (payload) => api.put('/api/profile', payload);

// ---------- AI Premium features ----------
export const aiSummary    = (text) => api.post('/api/ai/summary', { text });
export const aiFlashcards = (text) => api.post('/api/ai/flashcards', { text });
export const aiQuiz       = (text) => api.post('/api/ai/quiz', { text });
export const aiConcepts   = (titles) => api.post('/api/ai/concepts', { titles });
export const aiStreakCoach = (payload) => api.post('/api/ai/streak-coach', payload);

export default api;
