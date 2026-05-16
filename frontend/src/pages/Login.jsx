import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { getGoogleAuthUrl } from '../services/api';

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: '', password: '' });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (window.__googleAuthError === 'not_registered') {
      toast.error('That Google account is not registered yet — please sign up first.');
      delete window.__googleAuthError;
    }
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await login(form.username, form.password);
      toast.success('Welcome back 👋');
      nav('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Login failed');
    } finally { setBusy(false); }
  };

  const google = async () => {
    try {
      const r = await getGoogleAuthUrl('login');
      if (r.data?.url) window.location.href = r.data.url;
    } catch { toast.error('Google login unavailable'); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="card p-8 w-full max-w-md"
      >
        <Link to="/" className="flex items-center gap-2 mb-6">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white">📚</div>
          <span className="font-display font-bold text-lg">LearnFlow</span>
        </Link>

        <div className="pill-peach mb-3">🎁 Premium is FREE for 30 days</div>
        <h1 className="font-display text-2xl font-bold mb-1">Welcome back</h1>
        <p className="text-sm text-ink-muted mb-6">Sign in to pick up where you left off.</p>

        <form onSubmit={submit} className="space-y-4">
          <div>
            <div className="label mb-1">Username</div>
            <input className="input" required value={form.username}
              onChange={e => setForm({ ...form, username: e.target.value })} />
          </div>
          <div>
            <div className="label mb-1">Password</div>
            <input type="password" className="input" required value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })} />
          </div>
          <button type="submit" disabled={busy} className="btn-primary w-full !py-3">
            {busy ? '…' : 'Sign in'}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3 text-xs text-ink-muted">
          <div className="flex-1 h-px bg-indigo-100" /> or <div className="flex-1 h-px bg-indigo-100" />
        </div>

        <button onClick={google} className="btn-secondary w-full">
          <span>🅖</span> Continue with Google
        </button>

        <div className="text-center text-sm text-ink-muted mt-6">
          New here? <Link to="/register" className="text-indigo-600 font-semibold">Create an account</Link>
        </div>
      </motion.div>
    </div>
  );
}
