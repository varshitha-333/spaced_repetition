import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

export const getToken = () => localStorage.getItem('auth_token');
export const setToken = (token) => localStorage.setItem('auth_token', token);
export const clearToken = () => localStorage.removeItem('auth_token');

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: false,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error)
);

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
export const getGoogleAuthUrl = (mode = 'login') => api.get('/api/auth/google', { params: { mode } });
export const connectDrive = () => api.get('/api/drive/connect');
export const disconnectDrive = () => api.post('/api/drive/disconnect');

export const uploadPreview = (formData) =>
  api.post('/api/upload/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const uploadSave = (data) => api.post('/api/upload/save', data);

export const getTodayRevisions = () => api.get('/api/revisions/today');
export const getOverdueRevisions = () => api.get('/api/revisions/overdue');
export const getCompletedRevisions = () => api.get('/api/revisions/completed');
export const getUpcomingRevisions = () => api.get('/api/revisions/upcoming');
export const getRevisionStats = () => api.get('/api/revisions/stats');

export const completeRevision = (id) => api.post(`/api/revisions/${id}/complete`);
export const postponeRevision = (id) => api.post(`/api/revisions/${id}/postpone`);
export const skipRevision = (id) => api.post(`/api/revisions/${id}/skip`);

export const getLearnings = () => api.get('/api/learnings');

export const getNotificationPreferences = () => api.get('/api/notifications/preferences');
export const saveNotificationPreferences = (payload) => api.put('/api/notifications/preferences', payload);

export default api;
