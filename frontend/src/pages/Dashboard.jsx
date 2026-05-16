import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  getTodayRevisions, getOverdueRevisions, getRevisionStats,
  completeRevision, postponeRevision,
  getPremiumStatus, enableSms, aiStreakCoach,
} from '../services/api';
import { useAuth } from '../hooks/useAuth';
import Navbar from '../components/Navbar';

const tone = (n) => n === 0 ? 'sage' : n < 3 ? 'indigo' : 'peach';

export default function Dashboard() {
  const { user, refreshUser } = useAuth();
  const nav = useNavigate();

  const [today, setToday] = useState([]);
  const [overdue, setOverdue] = useState([]);
  const [stats, setStats] = useState(null);
  const [premium, setPremium] = useState(null);
  const [coachMsg, setCoachMsg] = useState('');
  const [busy, setBusy] = useState(null);
  const [showSms, setShowSms] = useState(false);
  const [smsPhone, setSmsPhone] = useState(user?.notification_phone || '');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [t, o, s, p] = await Promise.all([
        getTodayRevisions(), getOverdueRevisions(), getRevisionStats(), getPremiumStatus(),
      ]);
      setToday(t.data?.revisions || []);
      setOverdue(o.data?.revisions || []);
      setStats(s.data || null);
      setPremium(p.data);
    } catch (e) {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Streak coach (premium-only) — fetch a Gemini-written line once data is ready
  useEffect(() => {
    if (!premium?.is_premium || !stats) return;
    aiStreakCoach({
      streak: stats.current_streak || 0,
      done_today: stats.completed_today || 0,
      due_today: today.length,
    }).then(r => setCoachMsg(r.data?.message || '')).catch(() => {});
  }, [premium, stats, today.length]);

  const handleComplete = async (id) => {
    setBusy(id);
    try {
      await completeRevision(id);
      toast.success('Nice — locked in. 🎯');
      load();
    } catch { toast.error('Could not save'); }
    finally { setBusy(null); }
  };
  const handlePostpone = async (id) => {
    setBusy(id);
    try {
      await postponeRevision(id);
      toast('Pushed to tomorrow', { icon: '⏭️' });
      load();
    } catch { toast.error('Could not postpone'); }
    finally { setBusy(null); }
  };

  const handleEnableSms = async () => {
    if (!smsPhone.trim()) { toast.error('Enter your phone number'); return; }
    try {
      const r = await enableSms(smsPhone.trim(), true);
      toast.success(r.data.sms?.mode === 'real' ? 'SMS reminders enabled!' : 'Enabled (mock — set Twilio env vars for real SMS)');
      setShowSms(false);
      refreshUser();
    } catch (e) { toast.error(e.response?.data?.error || 'Failed'); }
  };

  const driveConnected = !!user?.drive_connected;
  const totalDue = today.length + overdue.length;
  const allDone = !loading && totalDue === 0;

  return (
    <div className="min-h-screen">
      <Navbar />

      {/* ─────────── Premium ribbon ─────────── */}
      {premium && !premium.is_premium && premium.campaign_active && (
        <div className="bg-gradient-to-r from-indigo-600 via-indigo-500 to-peach-500 text-white text-sm py-2 px-4 text-center">
          🎁 Launch offer · Premium is <b>FREE for 30 days</b>.{' '}
          <Link to="/pricing" className="underline font-semibold ml-1">Claim now →</Link>
        </div>
      )}
      {premium?.is_premium && (
        <div className="bg-emerald-50 border-b border-emerald-100 text-emerald-800 text-sm py-2 px-4 text-center">
          ✨ You're on Premium · {premium.days_left} days left ·{' '}
          <Link to="/premium" className="underline font-semibold">Open AI Lab →</Link>
        </div>
      )}

      <div className="container-page py-8">
        {/* ─────────── Heading + Streak ─────────── */}
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8"
        >
          <div>
            <div className="text-sm text-ink-muted">Good {greet()}, {user?.username || 'student'} 👋</div>
            <h1 className="font-display text-3xl sm:text-4xl font-bold">
              {allDone ? "You're all caught up." : `Let's do today's ${totalDue} revisions.`}
            </h1>
            {coachMsg && (
              <div className="mt-2 text-sm text-indigo-700 bg-indigo-50/70 inline-block px-3 py-1.5 rounded-lg">
                💬 {coachMsg}
              </div>
            )}
          </div>
          <div className="flex gap-3">
            <Stat label="Streak" value={`${stats?.current_streak || 0}🔥`} tone="peach" />
            <Stat label="Done today" value={stats?.completed_today ?? 0} tone="sage" />
            <Stat label="Saved" value={stats?.total_learnings ?? 0} tone="indigo" />
          </div>
        </motion.div>

        {/* ─────────── Today's focus ─────────── */}
        <section className="mb-8">
          <SectionHeader title="Today's revisions" badge={`${today.length}`} tone={tone(today.length)} action={<Link to="/today" className="btn-ghost text-sm">See full focus mode →</Link>} />
          {loading ? <SkeletonRows /> : today.length === 0 ? (
            <EmptyToday />
          ) : (
            <div className="grid md:grid-cols-2 gap-3">
              {today.slice(0, 6).map(r => (
                <RevisionCard key={r.id} r={r} onDone={() => handleComplete(r.id)} onLater={() => handlePostpone(r.id)} busy={busy === r.id} />
              ))}
            </div>
          )}
        </section>

        {/* ─────────── Overdue ─────────── */}
        {overdue.length > 0 && (
          <section className="mb-8">
            <SectionHeader title="Catching up" badge={`${overdue.length} overdue`} tone="peach" />
            <div className="grid md:grid-cols-2 gap-3">
              {overdue.slice(0, 4).map(r => (
                <RevisionCard key={r.id} r={r} overdue onDone={() => handleComplete(r.id)} onLater={() => handlePostpone(r.id)} busy={busy === r.id} />
              ))}
            </div>
          </section>
        )}

        {/* ─────────── Quick actions ─────────── */}
        <section className="grid md:grid-cols-3 gap-4 mb-8">
          <QuickCard
            tone="indigo" icon="📥"
            title="Add a new resource"
            desc="PDF, link, or pasted notes. AI titles it for you."
            cta="Add now"
            onClick={() => nav('/upload')}
          />
          <QuickCard
            tone="peach" icon="📱"
            title="Enable SMS reminders"
            desc="One number, two friendly nudges per day. 8 AM + 9 PM."
            cta={user?.sms_notifications_enabled ? 'Manage' : 'Turn on'}
            onClick={() => setShowSms(true)}
          />
          <QuickCard
            tone="sage" icon={driveConnected ? '✅' : '🔗'}
            title={driveConnected ? 'Google Drive connected' : 'Connect Google Drive'}
            desc={driveConnected ? 'Your uploads sync to your own Drive automatically.' : 'Sync your resources to your own Drive folder.'}
            cta={driveConnected ? 'Manage' : 'Connect'}
            onClick={() => nav('/profile')}
          />
        </section>

        {/* ─────────── Premium teaser (only if not premium) ─────────── */}
        {!premium?.is_premium && (
          <motion.div
            initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
            className="premium-ribbon rounded-2xl p-6 sm:p-8 text-white relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-40 h-40 rounded-full bg-white/10" />
            <div className="grid md:grid-cols-2 gap-4 items-center relative">
              <div>
                <div className="pill bg-white/20 text-white mb-2">🎁 Premium · 30 days FREE</div>
                <h3 className="text-2xl font-display font-bold mb-2">Unlock AI summaries, flashcards & quizzes</h3>
                <p className="opacity-90 text-sm">
                  Use code <code className="bg-white/20 px-1.5 py-0.5 rounded">LAUNCH30</code> at checkout — total today is ₹0.
                </p>
              </div>
              <div className="flex md:justify-end">
                <Link to="/payment" className="bg-white text-indigo-700 font-semibold rounded-xl px-5 py-2.5 hover:bg-white/95 shadow-lift">
                  Claim Premium →
                </Link>
              </div>
            </div>
          </motion.div>
        )}
      </div>

      {/* ─────────── SMS modal ─────────── */}
      {showSms && (
        <div className="fixed inset-0 z-50 bg-ink/40 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in">
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}
            className="card p-6 max-w-md w-full"
          >
            <div className="text-2xl mb-2">📱</div>
            <h3 className="font-display text-xl font-bold mb-1">Enable SMS reminders</h3>
            <p className="text-sm text-ink-muted mb-4">
              You'll get a calm nudge at <b>8 AM</b> with what to revise, and a quick recap at <b>9 PM</b>.
            </p>
            <input
              className="input mb-4" placeholder="+91 9876543210" value={smsPhone}
              onChange={e => setSmsPhone(e.target.value)}
            />
            {!user?.twilio_configured && (
              <div className="text-xs text-amber-700 bg-amber-50 rounded-lg p-2 mb-3">
                Twilio env vars not set on server — SMS will run in mock mode (logged to console).
              </div>
            )}
            <div className="flex gap-2">
              <button onClick={() => setShowSms(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={handleEnableSms} className="btn-primary flex-1">Turn on</button>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}

/* ─────────── small helpers ─────────── */
function greet() {
  const h = new Date().getHours();
  if (h < 12) return 'morning'; if (h < 18) return 'afternoon'; return 'evening';
}

function Stat({ label, value, tone }) {
  const bg = tone === 'peach' ? 'bg-peach-100 text-peach-600'
    : tone === 'sage' ? 'bg-emerald-100 text-emerald-700'
    : 'bg-indigo-100 text-indigo-700';
  return (
    <div className="card px-4 py-3 min-w-[110px]">
      <div className="text-xs text-ink-muted">{label}</div>
      <div className={`text-xl font-bold ${bg.split(' ')[1]}`}>{value}</div>
    </div>
  );
}

function SectionHeader({ title, badge, tone = 'indigo', action }) {
  const cls = tone === 'peach' ? 'pill-peach' : tone === 'sage' ? 'pill-sage' : 'pill-indigo';
  return (
    <div className="flex items-center mb-3">
      <h2 className="font-display text-xl font-semibold">{title}</h2>
      {badge && <span className={`${cls} ml-3`}>{badge}</span>}
      <div className="flex-1" />
      {action}
    </div>
  );
}

function SkeletonRows() {
  return (
    <div className="grid md:grid-cols-2 gap-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="card p-5 space-y-2">
          <div className="shimmer h-4 w-3/4" />
          <div className="shimmer h-3 w-1/2" />
        </div>
      ))}
    </div>
  );
}

function EmptyToday() {
  return (
    <div className="card p-8 text-center">
      <div className="text-4xl mb-2">🌿</div>
      <div className="font-semibold mb-1">Nothing due right now.</div>
      <div className="text-sm text-ink-muted">Add a new resource — your future self will thank you.</div>
      <Link to="/upload" className="btn-primary mt-4 inline-flex">+ Add resource</Link>
    </div>
  );
}

function RevisionCard({ r, overdue, onDone, onLater, busy }) {
  return (
    <div className={`card p-4 card-hover ${overdue ? 'border-peach-200/80 bg-peach-50/40' : ''}`}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={overdue ? 'pill-peach' : 'pill-indigo'}>
              {overdue ? 'Overdue' : `Day ${r.day_number || ''}`}
            </span>
            {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline truncate">open ↗</a>}
          </div>
          <div className="font-semibold text-ink truncate">{r.heading || r.title || 'Untitled'}</div>
          {r.description && <div className="text-sm text-ink-muted line-clamp-2 mt-1">{r.description}</div>}
        </div>
      </div>
      <div className="flex gap-2 mt-3">
        <button disabled={busy} onClick={onDone} className="btn-primary flex-1 !py-2 text-sm">
          {busy ? '…' : '✓ Done'}
        </button>
        <button disabled={busy} onClick={onLater} className="btn-secondary !py-2 text-sm">Later</button>
      </div>
    </div>
  );
}

function QuickCard({ tone, icon, title, desc, cta, onClick }) {
  const bg = tone === 'peach' ? 'from-peach-50 to-cream-50'
    : tone === 'sage' ? 'from-emerald-50 to-cream-50'
    : 'from-indigo-50 to-cream-50';
  return (
    <button onClick={onClick} className={`text-left card card-hover p-5 bg-gradient-to-br ${bg}`}>
      <div className="text-2xl mb-2">{icon}</div>
      <div className="font-semibold mb-1">{title}</div>
      <div className="text-sm text-ink-muted mb-3">{desc}</div>
      <span className="text-sm font-semibold text-indigo-700">{cta} →</span>
    </button>
  );
}
