import { useState, useEffect, useMemo } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import {
  getRevisionStats,
  connectDrive,
  disconnectDrive,
  saveNotificationPreferences,
} from '../utils/api';
import StatsCard from '../components/StatsCard';
import toast from 'react-hot-toast';
import {
  FiUpload,
  FiCalendar,
  FiClock,
  FiCheckCircle,
  FiAlertTriangle,
  FiLink,
  FiLink2,
  FiSmartphone,
  FiArrowRight,
  FiZap,
  FiCloud,
  FiShield,
  FiStar,
  FiTrendingUp,
} from 'react-icons/fi';

const planTiers = [
  {
    name: 'Free',
    price: '₹0',
    subtitle: 'For students building a habit',
    accent: 'from-slate-500 to-slate-700',
    border: 'border-slate-200',
    features: ['Core spaced repetition flow', 'Manual daily review tracking', 'Basic upload + AI title generation'],
  },
  {
    name: 'Core',
    price: '₹199/mo',
    subtitle: 'For consistent learners',
    accent: 'from-primary-500 to-primary-700',
    border: 'border-primary-300',
    featured: true,
    features: ['Morning SMS reminders at 8 AM', 'Google Drive sync visibility', 'Upcoming review management with calmer UI'],
  },
  {
    name: 'Premium',
    price: '₹499/mo',
    subtitle: 'For exam season and heavy workloads',
    accent: 'from-amber-400 to-orange-500',
    border: 'border-amber-200',
    features: ['Priority nudges for overdue revisions', 'Advanced analytics + streak coaching', 'Future scope for smart AI study concierge'],
  },
];

export default function Dashboard() {
  const { user, checkAuth } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingNotification, setSavingNotification] = useState(false);
  const [searchParams] = useSearchParams();
  const browserTimezone = useMemo(
    () => Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
    []
  );
  const [notificationPhone, setNotificationPhone] = useState('');
  const [notificationEnabled, setNotificationEnabled] = useState(false);

  useEffect(() => {
    fetchStats();
    const driveStatus = searchParams.get('drive');
    const loginStatus = searchParams.get('login');

    if (driveStatus === 'connected') {
      toast.success('Google Drive connected!');
      checkAuth();
    }
    if (driveStatus === 'error') toast.error('Drive connection failed');
    if (loginStatus === 'success') {
      toast.success('Welcome!');
      checkAuth();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setNotificationPhone(user?.notification_phone || '');
    setNotificationEnabled(Boolean(user?.sms_notifications_enabled));
  }, [user]);

  const fetchStats = async () => {
    try {
      const res = await getRevisionStats();
      setStats(res.data);
    } catch {
      toast.error('Failed to load stats');
    } finally {
      setLoading(false);
    }
  };

  const handleConnectDrive = async () => {
    try {
      const res = await connectDrive();
      window.location.href = res.data.auth_url;
    } catch {
      toast.error('Could not connect Drive');
    }
  };

  const handleChangeDrive = async () => {
    try {
      const res = await connectDrive();
      window.location.href = res.data.auth_url;
    } catch {
      toast.error('Could not re-connect Drive');
    }
  };

  const handleDisconnectDrive = async () => {
    try {
      await disconnectDrive();
      toast.success('Drive disconnected');
      checkAuth();
    } catch {
      toast.error('Failed to disconnect');
    }
  };

  const handleSaveNotifications = async () => {
    setSavingNotification(true);
    try {
      await saveNotificationPreferences({
        enabled: notificationEnabled,
        phone_number: notificationPhone,
        timezone: browserTimezone,
        notification_hour: 8,
      });
      await checkAuth();
      toast.success(notificationEnabled ? 'Morning SMS reminders enabled' : 'Morning SMS reminders updated');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Could not save SMS settings');
    } finally {
      setSavingNotification(false);
    }
  };

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  const dueLogicLabels = stats?.due_logic?.labels || ['Day 1', 'Day 3', 'Day 6', 'Day 29', 'Day 179'];
  const driveConnected = Boolean(user?.drive_connected);
  const twilioReady = Boolean(user?.twilio_configured);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="rounded-[28px] overflow-hidden border border-white/60 bg-white/70 backdrop-blur-xl shadow-soft">
          <div className="bg-gradient-to-r from-primary-600 via-primary-500 to-accent-500 p-[1px]">
            <div className="bg-gradient-to-br from-slate-950 via-primary-950 to-slate-900 rounded-[27px] text-white px-6 sm:px-8 py-7 sm:py-9">
              <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6">
                <div className="max-w-2xl">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/10 text-white/85 text-xs font-semibold mb-4">
                    <FiZap size={14} /> Smart spaced repetition for students
                  </div>
                  <h1 className="text-3xl sm:text-4xl font-extrabold leading-tight mb-2">
                    {greeting()}, {user?.username}! Let&apos;s make today&apos;s revision lighter.
                  </h1>
                  <p className="text-white/75 text-sm sm:text-base max-w-xl">
                    LearnFlow now surfaces clear drive status, calmer upcoming tasks, and optional Twilio-powered morning reminders with motivational quotes.
                  </p>
                </div>
                <div className="grid grid-cols-2 gap-3 sm:min-w-[320px]">
                  <Link to="/upload" className="rounded-2xl bg-white text-slate-900 px-4 py-4 font-semibold flex items-center justify-between hover:-translate-y-0.5 transition-all">
                    <span className="flex items-center gap-2"><FiUpload size={18} /> Add material</span>
                    <FiArrowRight />
                  </Link>
                  <Link to="/today" className="rounded-2xl bg-white/10 border border-white/15 px-4 py-4 font-semibold flex items-center justify-between hover:bg-white/15 transition-all">
                    <span className="flex items-center gap-2"><FiCalendar size={18} /> Today&apos;s queue</span>
                    <FiArrowRight />
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </motion.div>

      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="glass-card p-5 animate-pulse">
              <div className="h-12 w-12 bg-gray-200 rounded-2xl mb-3" />
              <div className="h-6 w-16 bg-gray-200 rounded mb-2" />
              <div className="h-4 w-24 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatsCard icon="📅" label="Due Today" value={stats.today} color="primary" delay={0.1} subtitle="Needs attention now" />
          <StatsCard icon="⚠️" label="Overdue" value={stats.overdue} color={stats.overdue > 0 ? 'danger' : 'success'} delay={0.2} subtitle="Carry-forward items" />
          <StatsCard icon="✅" label="Completed Today" value={stats.completed_today} color="success" delay={0.3} subtitle="Progress already made" />
          <StatsCard icon="🔥" label="Current Streak" value={`${stats.streak} day${stats.streak !== 1 ? 's' : ''}`} color="warning" delay={0.4} subtitle="Protect it today" />
        </div>
      )}

      <div className="grid xl:grid-cols-[1.1fr_0.9fr] gap-6 mb-8">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2 }}
          className="space-y-6"
        >
          <div className="glass-card p-6">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div>
                <h2 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                  <FiCloud className="text-primary-600" /> Google Drive status
                </h2>
                <p className="text-sm text-gray-500 mt-1">A clearer connected status so you can trust your backup flow.</p>
              </div>
              <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${driveConnected ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'}`}>
                <span className={`w-2 h-2 rounded-full ${driveConnected ? 'bg-emerald-500' : 'bg-gray-400'}`} />
                {driveConnected ? 'Drive connected' : 'Drive not connected'}
              </span>
            </div>

            {driveConnected ? (
              <div className="space-y-4">
                <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-2xl bg-emerald-100 flex items-center justify-center shrink-0">
                      <FiCheckCircle className="text-emerald-600" size={22} />
                    </div>
                    <div>
                      <p className="font-semibold text-emerald-700">Connection verified</p>
                      <p className="text-sm text-emerald-600 mt-1">
                        LearnFlow can store synced file links and keep your uploaded study material accessible from your dashboard.
                      </p>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap gap-3">
                  <button onClick={handleChangeDrive} className="btn-secondary text-sm flex items-center gap-2">
                    <FiLink2 size={14} /> Change account
                  </button>
                  <button onClick={handleDisconnectDrive} className="text-sm text-red-500 hover:text-red-600 font-medium hover:underline">
                    Disconnect drive
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="rounded-2xl border border-dashed border-primary-200 bg-primary-50/70 p-4 text-sm text-gray-600">
                  Connect Google Drive if you want an extra storage layer for uploaded documents and easier access to your learning links.
                </div>
                <button onClick={handleConnectDrive} className="btn-secondary w-full sm:w-auto flex items-center justify-center gap-2 text-sm">
                  <FiLink2 size={16} /> Connect Google Drive
                </button>
              </div>
            )}
          </div>

          <div className="glass-card p-6">
            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <h2 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                  <FiTrendingUp className="text-primary-600" /> Meaningful due logic
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Designed around spaced repetition so difficult memories come back before they fade.
                </p>
              </div>
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary-50 text-primary-600 text-xs font-semibold">
                <FiShield size={14} /> Memory-first schedule
              </div>
            </div>

            <div className="flex flex-wrap gap-2 mb-4">
              {dueLogicLabels.map((label) => (
                <span key={label} className="px-3 py-2 rounded-xl bg-primary-50 text-primary-700 text-sm font-semibold border border-primary-100">
                  {label}
                </span>
              ))}
            </div>

            <div className="grid sm:grid-cols-3 gap-3 text-sm">
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <p className="font-semibold text-gray-800 mb-1">When a topic is added</p>
                <p className="text-gray-500">The app schedules reviews for Day 1, 3, 6, 29 and 179 to reinforce memory over short and long gaps.</p>
              </div>
              <div className="rounded-2xl bg-amber-50 border border-amber-100 p-4">
                <p className="font-semibold text-gray-800 mb-1">If you miss a day</p>
                <p className="text-gray-500">The task becomes overdue and stays visible until you finish it, so weak recall doesn&apos;t silently disappear.</p>
              </div>
              <div className="rounded-2xl bg-emerald-50 border border-emerald-100 p-4">
                <p className="font-semibold text-gray-800 mb-1">Why the streak matters</p>
                <p className="text-gray-500">When all due work is cleared, your streak grows. That rewards consistency, not random cramming.</p>
              </div>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.25 }}
          className="space-y-6"
        >
          <div className="glass-card p-6">
            <div className="flex items-start justify-between gap-4 mb-5">
              <div>
                <h2 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                  <FiSmartphone className="text-primary-600" /> 8 AM Twilio reminder
                </h2>
                <p className="text-sm text-gray-500 mt-1">
                  Uses your existing username, includes today&apos;s revision links, overdue carry-forward, streak, and a different motivation quote each day.
                </p>
              </div>
              <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold ${twilioReady ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                {twilioReady ? 'Twilio ready' : 'Twilio env pending'}
              </span>
            </div>

            <div className="space-y-4">
              <label className="flex items-start gap-3 rounded-2xl border border-gray-200 bg-white/70 px-4 py-4 cursor-pointer">
                <input
                  type="checkbox"
                  checked={notificationEnabled}
                  onChange={(e) => setNotificationEnabled(e.target.checked)}
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                />
                <div>
                  <p className="font-semibold text-gray-800">Send morning revision SMS</p>
                  <p className="text-sm text-gray-500 mt-1">
                    Daily delivery at 8:00 AM in your browser timezone: <span className="font-medium text-gray-700">{browserTimezone}</span>
                  </p>
                </div>
              </label>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Phone number in international format</label>
                <input
                  type="tel"
                  value={notificationPhone}
                  onChange={(e) => setNotificationPhone(e.target.value)}
                  className="input-field"
                  placeholder="+14155550100 or +919876543210"
                />
                <p className="text-xs text-gray-400 mt-2">
                  Example: include country code. Your LearnFlow username is automatically used in the message greeting.
                </p>
              </div>

              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4 text-sm text-gray-600 space-y-2">
                <p className="font-semibold text-gray-800">Message includes</p>
                <ul className="space-y-1.5 list-disc pl-5">
                  <li>all revision links due today</li>
                  <li>carry-forward items from previous days</li>
                  <li>your current streak and a fresh quote</li>
                </ul>
              </div>

              <button onClick={handleSaveNotifications} disabled={savingNotification} className="btn-primary w-full flex items-center justify-center gap-2 text-sm">
                {savingNotification ? <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <><FiSmartphone size={16} /> Save SMS settings</>}
              </button>

              {!twilioReady && (
                <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700">
                  Add Twilio and notification environment variables in Render before enabling this for production.
                </div>
              )}
            </div>
          </div>

          <div className="glass-card p-6">
            <div className="flex items-center justify-between gap-4 mb-4">
              <div>
                <h2 className="font-bold text-gray-800 text-lg flex items-center gap-2">
                  <FiClock className="text-primary-600" /> Coming up
                </h2>
                <p className="text-sm text-gray-500 mt-1">A calmer preview before you open the full upcoming page.</p>
              </div>
              <Link to="/upcoming" className="text-sm text-primary-600 font-semibold hover:underline">
                Open upcoming →
              </Link>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-blue-50 border border-blue-100 p-4">
                <p className="text-xs uppercase tracking-wide text-blue-500 font-semibold mb-2">Tomorrow</p>
                <p className="text-2xl font-bold text-blue-700">{stats?.tomorrow || 0}</p>
                <p className="text-sm text-blue-600 mt-1">scheduled revisions</p>
              </div>
              <div className="rounded-2xl bg-purple-50 border border-purple-100 p-4">
                <p className="text-xs uppercase tracking-wide text-purple-500 font-semibold mb-2">Later queue</p>
                <p className="text-2xl font-bold text-purple-700">{stats?.future || 0}</p>
                <p className="text-sm text-purple-600 mt-1">future tasks</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35 }}
        className="mb-8"
      >
        <div className="flex items-end justify-between gap-4 mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-800 flex items-center gap-2">
              <FiStar className="text-accent-500" /> Student SaaS tiers
            </h2>
            <p className="text-sm text-gray-500 mt-1">You asked for Free, Core, and Premium positioning. This section shows the product differentiation in the UI.</p>
          </div>
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          {planTiers.map((tier, idx) => (
            <motion.div
              key={tier.name}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 * idx }}
              className={`relative rounded-[26px] border ${tier.border} bg-white/80 backdrop-blur-xl p-6 shadow-soft ${tier.featured ? 'ring-2 ring-primary-200' : ''}`}
            >
              {tier.featured && (
                <span className="absolute -top-3 left-6 px-3 py-1 rounded-full text-xs font-bold bg-primary-600 text-white shadow-lg">
                  Best for most students
                </span>
              )}
              <div className={`inline-flex rounded-2xl px-3 py-2 text-white bg-gradient-to-r ${tier.accent} text-sm font-bold mb-4`}>
                {tier.name}
              </div>
              <h3 className="text-2xl font-bold text-gray-900">{tier.price}</h3>
              <p className="text-sm text-gray-500 mt-1 mb-5">{tier.subtitle}</p>
              <div className="space-y-3">
                {tier.features.map((feature) => (
                  <div key={feature} className="flex items-start gap-3 text-sm text-gray-700">
                    <span className="mt-0.5 w-5 h-5 rounded-full bg-primary-50 text-primary-600 flex items-center justify-center shrink-0">✓</span>
                    <span>{feature}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
