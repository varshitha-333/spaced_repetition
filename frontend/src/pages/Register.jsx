import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { getGoogleAuthUrl } from '../services/api';

export default function Register() {
  const { register } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (form.password.length < 6) { toast.error('Password too short'); return; }
    setBusy(true);
    try {
      await register(form.username, form.password, form.email);
      toast.success('Welcome to LearnFlow! 🎉');
      nav('/payment');   // send straight to free-Premium claim
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not register');
    } finally { setBusy(false); }
  };

  const google = async () => {
    try {
      const r = await getGoogleAuthUrl('register');
      if (r.data?.url) window.location.href = r.data.url;
    } catch { toast.error('Google sign-up unavailable'); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
        className="grid md:grid-cols-2 gap-0 w-full max-w-4xl card overflow-hidden"
      >
        {/* Left: form */}
        <div className="p-8">
          <Link to="/" className="flex items-center gap-2 mb-6">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white">📚</div>
            <span className="font-display font-bold text-lg">LearnFlow</span>
          </Link>

          <h1 className="font-display text-2xl font-bold mb-1">Create your account</h1>
          <p className="text-sm text-ink-muted mb-6">It's free. Premium is on us for 30 days.</p>

          <form onSubmit={submit} className="space-y-4">
            <div>
              <div className="label mb-1">Username</div>
              <input className="input" required value={form.username}
                onChange={e => setForm({ ...form, username: e.target.value })} />
            </div>
            <div>
              <div className="label mb-1">Email</div>
              <input type="email" className="input" required value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })} />
            </div>
            <div>
              <div className="label mb-1">Password</div>
              <input type="password" className="input" required value={form.password}
                onChange={e => setForm({ ...form, password: e.target.value })}
                placeholder="At least 6 characters" />
            </div>
            <button type="submit" disabled={busy} className="btn-primary w-full !py-3">
              {busy ? '…' : 'Create account & claim Premium 🎁'}
            </button>
          </form>

          <div className="my-5 flex items-center gap-3 text-xs text-ink-muted">
            <div className="flex-1 h-px bg-indigo-100" /> or <div className="flex-1 h-px bg-indigo-100" />
          </div>

          <button onClick={google} className="btn-secondary w-full">
            <span>🅖</span> Continue with Google
          </button>

          <div className="text-center text-sm text-ink-muted mt-6">
            Already have an account? <Link to="/login" className="text-indigo-600 font-semibold">Sign in</Link>
          </div>
        </div>

        {/* Right: promo */}
        <div className="hidden md:flex flex-col justify-center p-8 premium-ribbon text-white relative overflow-hidden">
          <div className="absolute -top-10 -right-10 w-44 h-44 rounded-full bg-white/10 animate-float" />
          <div className="absolute -bottom-10 -left-8 w-40 h-40 rounded-full bg-white/10 animate-float" style={{ animationDelay: '1s' }} />
          <div className="relative">
            <div className="pill bg-white/20 text-white mb-3">🎁 Launch offer</div>
            <h2 className="font-display text-3xl font-bold mb-3 leading-tight">
              Premium FREE for 30 days
            </h2>
            <ul className="space-y-2 text-sm opacity-95">
              <li>✓ AI Smart Summary</li>
              <li>✓ AI Flashcards & Quizzes</li>
              <li>✓ Concept Linker</li>
              <li>✓ 8 AM + 9 PM SMS reminders</li>
              <li>✓ Streak coach</li>
            </ul>
            <div className="mt-5 text-xs opacity-80">
              Coupons: LAUNCH30 · STUDENT30 · FIRST100 · LEARNFREE
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
