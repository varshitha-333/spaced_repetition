import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  getProfile, updateProfile, submitReview,
  connectDrive, disconnectDrive,
  enableSms, testSms,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import Navbar from '../components/Navbar';

export default function Profile() {
  const { refreshUser } = useAuth();
  const [p, setP] = useState(null);
  const [form, setForm] = useState({ display_name: '', email: '', phone: '' });
  const [sms, setSms] = useState({ enabled: false, phone: '' });
  const [review, setReview] = useState({ rating: 5, text: '' });
  const [tab, setTab] = useState('profile');

  const load = () => getProfile().then(r => {
    setP(r.data);
    setForm({
      display_name: r.data.display_name || '',
      email: r.data.email || '',
      phone: r.data.phone || '',
    });
    setSms({ enabled: !!r.data.sms_enabled, phone: r.data.phone || '' });
  });

  useEffect(() => { load(); }, []);

  const saveProfile = async () => {
    try { await updateProfile(form); toast.success('Profile saved'); load(); refreshUser(); }
    catch (e) { toast.error(e.response?.data?.error || 'Failed'); }
  };

  const saveSms = async () => {
    if (sms.enabled && !sms.phone.trim()) { toast.error('Phone required'); return; }
    try {
      const r = await enableSms(sms.phone.trim(), sms.enabled);
      toast.success(r.data.sms?.mode === 'real' ? 'SMS settings saved (real)' : 'Saved (mock mode)');
      load(); refreshUser();
    } catch (e) { toast.error('Failed'); }
  };

  const sendTest = async () => {
    try { const r = await testSms(); toast.success(`Sent (${r.data.sms?.mode})`); }
    catch (e) { toast.error(e.response?.data?.error || 'Failed'); }
  };

  const handleDrive = async () => {
    if (p.drive_connected) {
      await disconnectDrive(); toast('Drive disconnected', { icon: '🔗' });
      load(); refreshUser();
    } else {
      const r = await connectDrive();
      const url = r.data?.url; if (url) window.location.href = url;
    }
  };

  const sendReview = async () => {
    if (review.text.trim().length < 10) { toast.error('Write a bit more 🙂'); return; }
    try {
      const r = await submitReview(review.rating, review.text, form.display_name || undefined);
      toast.success(`Thanks! Quality score ${r.data.quality_score}/10`);
      setReview({ rating: 5, text: '' });
    } catch (e) { toast.error(e.response?.data?.error || 'Failed'); }
  };

  if (!p) return null;

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-3xl font-bold mb-2">Your profile</h1>
          <p className="text-ink-muted mb-6">Update your info, control SMS reminders, and share a review.</p>
        </motion.div>

        {/* Premium status card */}
        <div className="card p-5 mb-6 flex flex-col sm:flex-row gap-3 items-start sm:items-center">
          {p.premium?.is_premium ? (
            <>
              <div className="text-3xl">✨</div>
              <div className="flex-1">
                <div className="font-semibold">Premium · active</div>
                <div className="text-sm text-ink-muted">
                  {p.premium.days_left} day{p.premium.days_left !== 1 && 's'} left ·
                  expires {new Date(p.premium.expires_at).toLocaleDateString()}
                </div>
              </div>
              <Link to="/premium" className="btn-primary">Open AI Lab</Link>
            </>
          ) : (
            <>
              <div className="text-3xl">🎁</div>
              <div className="flex-1">
                <div className="font-semibold">Free plan</div>
                <div className="text-sm text-ink-muted">Launch offer: Premium is free for 30 days. Use code LAUNCH30.</div>
              </div>
              <Link to="/payment" className="btn-peach">Try Premium FREE</Link>
            </>
          )}
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 card-quiet p-1 w-fit">
          {[
            { k: 'profile',  l: '👤 Profile' },
            { k: 'sms',      l: '📱 SMS reminders' },
            { k: 'drive',    l: '🔗 Google Drive' },
            { k: 'review',   l: '⭐ Leave a review' },
          ].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)}
              className={`px-3 py-1.5 rounded-lg text-sm transition ${tab === t.k ? 'bg-white shadow-soft text-ink font-semibold' : 'text-ink-soft hover:text-ink'}`}>
              {t.l}
            </button>
          ))}
        </div>

        {/* ─── Profile tab ─── */}
        {tab === 'profile' && (
          <div className="card p-6 space-y-4">
            <Field label="Username" value={p.username} disabled />
            <Field label="Display name" value={form.display_name} onChange={v => setForm({ ...form, display_name: v })} />
            <Field label="Email" value={form.email} onChange={v => setForm({ ...form, email: v })} />
            <Field label="Phone (for SMS)" value={form.phone} onChange={v => setForm({ ...form, phone: v })} />
            <button onClick={saveProfile} className="btn-primary">Save changes</button>
          </div>
        )}

        {/* ─── SMS tab ─── */}
        {tab === 'sms' && (
          <div className="card p-6 space-y-4">
            <div>
              <div className="font-semibold mb-1">Daily SMS reminders</div>
              <div className="text-sm text-ink-muted">
                Two calm nudges per day. Morning at <b>8 AM</b> (what to revise) · Night at <b>9 PM</b> (how it went).
              </div>
            </div>

            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={sms.enabled} onChange={e => setSms({ ...sms, enabled: e.target.checked })} className="w-5 h-5 accent-indigo-600" />
              <span>Enable SMS reminders</span>
            </label>
            <Field label="SMS number" value={sms.phone} onChange={v => setSms({ ...sms, phone: v })} placeholder="+91 9876543210" />

            <div className="flex flex-wrap gap-2">
              <button onClick={saveSms} className="btn-primary">Save SMS settings</button>
              <button onClick={sendTest} className="btn-secondary">Send test SMS</button>
            </div>
            <div className="text-xs text-ink-muted">
              Twilio mode is automatic: real SMS when env vars set, otherwise mock-logged on the server.
            </div>
          </div>
        )}

        {/* ─── Drive tab ─── */}
        {tab === 'drive' && (
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-3">
              <div className="text-3xl">{p.drive_connected ? '✅' : '🔗'}</div>
              <div className="flex-1">
                <div className="font-semibold">Google Drive · {p.drive_connected ? 'Connected' : 'Not connected'}</div>
                <div className="text-sm text-ink-muted">
                  {p.drive_connected
                    ? "We sync your saved resources to a 'LearnFlow' folder in your own Drive."
                    : "Connect to sync uploads to your own Drive folder automatically."}
                </div>
              </div>
              <button onClick={handleDrive} className={p.drive_connected ? 'btn-secondary' : 'btn-primary'}>
                {p.drive_connected ? 'Disconnect' : 'Connect Drive'}
              </button>
            </div>
            {p.drive_connected && (
              <div className="text-xs text-emerald-700 bg-emerald-50 rounded-lg p-3">
                Status is live — pulled from your saved credentials. If you see "not connected" elsewhere, refresh the page.
              </div>
            )}
          </div>
        )}

        {/* ─── Review tab ─── */}
        {tab === 'review' && (
          <div className="card p-6 space-y-4">
            <div>
              <div className="font-semibold mb-1">Leave a review</div>
              <div className="text-sm text-ink-muted">Top reviews (Gemini-scored) appear on our landing page.</div>
            </div>
            <div>
              <div className="label mb-1">Your rating</div>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map(n => (
                  <button key={n} onClick={() => setReview({ ...review, rating: n })}
                    className={`text-3xl transition ${n <= review.rating ? 'text-peach-500' : 'text-ink-muted/30'}`}>
                    ★
                  </button>
                ))}
              </div>
            </div>
            <div>
              <div className="label mb-1">Your review</div>
              <textarea rows={4} className="input" placeholder="What made LearnFlow click for you?"
                value={review.text} onChange={e => setReview({ ...review, text: e.target.value })} />
            </div>
            <button onClick={sendReview} className="btn-primary">Submit review</button>
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value, onChange, placeholder, disabled }) {
  return (
    <div>
      <div className="label mb-1">{label}</div>
      <input className="input" value={value || ''} disabled={disabled}
        placeholder={placeholder}
        onChange={onChange ? e => onChange(e.target.value) : undefined} />
    </div>
  );
}
