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
  const [sms, setSms] = useState({ enabled: false, countryCode: '+91', phone: '' });
  const [review, setReview] = useState({ rating: 5, text: '' });
  const [tab, setTab] = useState('profile');

  const load = async () => {
    try {
      const r = await getProfile();
      const data = r.data;
      setP(data);
      setForm({
        display_name: data.display_name || '',
        email: data.email || '',
        // ✅ FIX: profile returns 'phone' key
        phone: data.phone || '',
      });
      // ✅ FIX: sync SMS state from profile on load
      // Parse country code from existing phone number if present
      let countryCode = '+91';
      let phoneOnly = data.phone || '';
      if (phoneOnly && phoneOnly.startsWith('+')) {
        // Known country codes mapping (must match dropdown options exactly)
        const countryCodes = [
          '+971', '+353', '+65', '+64', '+46', '+47', '+45', '+31', '+39', '+34',
          '+1', '+44', '+91', '+61', '+81', '+86', '+49', '+33', '+7', '+55', '+52', '+27'
        ];
        
        // Sort by length (longest first) to match +971 before +1
        countryCodes.sort((a, b) => b.length - a.length);
        
        // Try to match known country codes
        let matched = false;
        for (const code of countryCodes) {
          if (phoneOnly.startsWith(code)) {
            countryCode = code;
            phoneOnly = phoneOnly.substring(code.length);
            matched = true;
            break;
          }
        }
        
        // If no known country code matched, use default extraction
        if (!matched) {
          const match = phoneOnly.match(/^\+(\d{1,4})(\d+)$/);
          if (match) {
            countryCode = '+' + match[1];
            phoneOnly = match[2];
          } else {
            // If regex fails, just remove the + and use default country code
            phoneOnly = phoneOnly.replace(/^\+/, '');
          }
        }
      }
      setSms({
        enabled: !!data.sms_enabled,
        countryCode: countryCode,
        phone: phoneOnly,
      });
    } catch (e) {
      toast.error('Failed to load profile');
    }
  };

  useEffect(() => { load(); }, []);

  const saveProfile = async () => {
    try {
      await updateProfile(form);
      toast.success('Profile saved ✓');
      load();
      refreshUser();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to save');
    }
  };

  const saveSms = async () => {
    if (sms.enabled && !sms.phone.trim()) {
      toast.error('Phone number required to enable SMS');
      return;
    }
    // Combine country code and phone number
    const fullPhone = sms.countryCode + sms.phone.replace(/\D/g, ''); // Remove non-digits
    try {
      const r = await enableSms(fullPhone, sms.enabled);
      const mode = r.data.sms?.mode;
      toast.success(mode === 'real' ? 'SMS settings saved!' : 'SMS settings saved (mock mode — add Twilio env vars for real SMS)');
      // ✅ FIX: also save phone to profile so it persists visibly
      if (sms.phone.trim()) {
        await updateProfile({ phone: fullPhone });
      }
      load();
      refreshUser();
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to save SMS settings');
    }
  };

  const sendTest = async () => {
    try {
      const r = await testSms();
      toast.success(`Test SMS sent (${r.data.sms?.mode})`);
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to send test');
    }
  };

  const handleDrive = async () => {
    if (p.drive_connected) {
      try {
        await disconnectDrive();
        toast('Drive disconnected', { icon: '🔗' });
        load();
        refreshUser();
      } catch {
        toast.error('Failed to disconnect');
      }
    } else {
      try {
        const r = await connectDrive();
        // ✅ FIX: backend returns auth_url not url
        const url = r.data?.auth_url || r.data?.url;
        if (url) window.location.href = url;
        else toast.error('Could not get Drive auth URL');
      } catch {
        toast.error('Failed to connect Drive');
      }
    }
  };

  const sendReview = async () => {
    if (review.text.trim().length < 10) {
      toast.error('Write a bit more 🙂');
      return;
    }
    try {
      const r = await submitReview(review.rating, review.text, form.display_name || undefined);
      toast.success(`Thanks! Quality score ${r.data.quality_score}/10`);
      setReview({ rating: 5, text: '' });
    } catch (e) {
      toast.error(e.response?.data?.error || 'Failed to submit review');
    }
  };

  if (!p) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-ink-muted">Loading profile…</div>
    </div>
  );

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
            { k: 'profile', l: '👤 Profile' },
            { k: 'sms',     l: '📱 SMS reminders' },
            { k: 'drive',   l: '🔗 Google Drive' },
            { k: 'review',  l: '⭐ Leave a review' },
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
            <Field label="Display name" value={form.display_name}
              onChange={v => setForm({ ...form, display_name: v })} />
            <Field label="Email" value={form.email}
              onChange={v => setForm({ ...form, email: v })} />
            <Field label="Phone (for SMS)" value={form.phone}
              onChange={v => setForm({ ...form, phone: v })}
              placeholder="+91 9876543210" />
            <button onClick={saveProfile} className="btn-primary">Save changes</button>
          </div>
        )}

        {/* ─── SMS tab ─── */}
        {tab === 'sms' && (
          <div className="card p-6 space-y-4">
            <div>
              <div className="font-semibold mb-1">Daily SMS reminders</div>
              <div className="text-sm text-ink-muted">
                Get daily SMS reminders for your revisions.
              </div>
            </div>
            <label className="flex items-center gap-3 cursor-pointer">
              <input type="checkbox" checked={sms.enabled}
                onChange={e => setSms({ ...sms, enabled: e.target.checked })}
                className="w-5 h-5 accent-indigo-600" />
              <span>Enable SMS reminders</span>
            </label>
            <div className="flex gap-2">
              <div className="flex-1">
                <div className="label mb-1">Country code</div>
                <select 
                  className="input"
                  value={sms.countryCode}
                  onChange={e => setSms({ ...sms, countryCode: e.target.value })}
                >
                  <option value="+1">+1 (USA/Canada)</option>
                  <option value="+44">+44 (UK)</option>
                  <option value="+91">+91 (India)</option>
                  <option value="+61">+61 (Australia)</option>
                  <option value="+81">+81 (Japan)</option>
                  <option value="+86">+86 (China)</option>
                  <option value="+49">+49 (Germany)</option>
                  <option value="+33">+33 (France)</option>
                  <option value="+971">+971 (UAE)</option>
                  <option value="+65">+65 (Singapore)</option>
                  <option value="+353">+353 (Ireland)</option>
                  <option value="+39">+39 (Italy)</option>
                  <option value="+34">+34 (Spain)</option>
                  <option value="+55">+55 (Brazil)</option>
                  <option value="+52">+52 (Mexico)</option>
                  <option value="+27">+27 (South Africa)</option>
                  <option value="+64">+64 (New Zealand)</option>
                  <option value="+31">+31 (Netherlands)</option>
                  <option value="+46">+46 (Sweden)</option>
                  <option value="+47">+47 (Norway)</option>
                  <option value="+45">+45 (Denmark)</option>
                </select>
              </div>
              <div className="flex-2">
                <div className="label mb-1">Phone number</div>
                <input 
                  className="input"
                  value={sms.phone}
                  onChange={e => setSms({ ...sms, phone: e.target.value.replace(/\D/g, '') })}
                  placeholder="9876543210"
                  maxLength={15}
                />
              </div>
            </div>
            <div className="text-xs text-ink-muted">
              Combined format: {sms.countryCode}{sms.phone}
            </div>
            <div className="flex flex-wrap gap-2">
              <button onClick={saveSms} className="btn-primary">Save SMS settings</button>
              <button onClick={sendTest} className="btn-secondary">Send test SMS</button>
            </div>
            {/* ✅ Show current saved state */}
            {p.sms_enabled && p.phone && (
              <div className="text-xs text-emerald-700 bg-emerald-50 rounded-lg p-2">
                ✓ SMS enabled for {p.phone}
              </div>
            )}
            <div className="text-xs text-ink-muted">
              Real SMS requires Twilio env vars. Otherwise mock-logged on the server.
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
                    : 'Connect to sync uploads to your own Drive folder automatically.'}
                </div>
              </div>
              <button onClick={handleDrive} className={p.drive_connected ? 'btn-secondary' : 'btn-primary'}>
                {p.drive_connected ? 'Disconnect' : 'Connect Drive'}
              </button>
            </div>
          </div>
        )}

        {/* ─── Review tab ─── */}
        {tab === 'review' && (
          <div className="card p-6 space-y-4">
            <div>
              <div className="font-semibold mb-1">Leave a review</div>
              <div className="text-sm text-ink-muted">Top reviews appear on our landing page.</div>
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
              <textarea rows={4} className="input"
                placeholder="What made LearnFlow click for you?"
                value={review.text}
                onChange={e => setReview({ ...review, text: e.target.value })} />
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
