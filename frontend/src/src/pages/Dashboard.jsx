import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { getRevisionStats, connectDrive, disconnectDrive } from '../utils/api';
import StatsCard from '../components/StatsCard';
import toast from 'react-hot-toast';
import {
  FiUpload, FiCalendar, FiClock, FiTrendingUp,
  FiCheckCircle, FiAlertTriangle, FiLink, FiLink2
} from 'react-icons/fi';

export default function Dashboard() {
  const { user, checkAuth } = useAuth();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    fetchStats();
    // Handle OAuth redirects
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
  }, []);

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

  const handleDisconnectDrive = async () => {
    try {
      await disconnectDrive();
      toast.success('Drive disconnected');
      checkAuth();
    } catch {
      toast.error('Failed to disconnect');
    }
  };

  const greeting = () => {
    const h = new Date().getHours();
    if (h < 12) return 'Good Morning';
    if (h < 17) return 'Good Afternoon';
    return 'Good Evening';
  };

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      {/* Hero Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-1">
              {greeting()}, <span className="gradient-text">{user?.username}</span>! 👋
            </h1>
            <p className="text-gray-500">Here's your learning overview for today</p>
          </div>
          <div className="flex gap-3">
            <Link to="/upload" className="btn-primary text-sm flex items-center gap-2">
              <FiUpload size={16} /> Add Material
            </Link>
            <Link to="/today" className="btn-secondary text-sm flex items-center gap-2">
              <FiCalendar size={16} /> Today's Tasks
            </Link>
          </div>
        </div>
      </motion.div>

      {/* Stats Grid */}
      {loading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="glass-card p-5 animate-pulse">
              <div className="h-12 w-12 bg-gray-200 rounded-2xl mb-3" />
              <div className="h-6 w-16 bg-gray-200 rounded mb-2" />
              <div className="h-4 w-24 bg-gray-100 rounded" />
            </div>
          ))}
        </div>
      ) : stats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatsCard icon="📅" label="Due Today" value={stats.today} color="primary" delay={0.1} />
          <StatsCard icon="⚠️" label="Overdue" value={stats.overdue} color={stats.overdue > 0 ? 'danger' : 'success'} delay={0.2} />
          <StatsCard icon="✅" label="Completed Today" value={stats.completed_today} color="success" delay={0.3} />
          <StatsCard
            icon="🔥"
            label="Current Streak"
            value={`${stats.streak} day${stats.streak !== 1 ? 's' : ''}`}
            color="warning"
            delay={0.4}
          />
        </div>
      )}

      {/* Quick Actions & Drive Status */}
      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3 }}
          className="glass-card p-6"
        >
          <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <span className="text-lg">⚡</span> Quick Actions
          </h2>
          <div className="grid grid-cols-2 gap-3">
            <Link to="/upload" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-primary-50 hover:bg-primary-100 transition-all text-center group">
              <div className="w-10 h-10 rounded-xl bg-primary-200 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FiUpload className="text-primary-700" size={20} />
              </div>
              <span className="text-sm font-medium text-primary-700">Upload PDF</span>
            </Link>
            <Link to="/upload" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-emerald-50 hover:bg-emerald-100 transition-all text-center group">
              <div className="w-10 h-10 rounded-xl bg-emerald-200 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FiLink className="text-emerald-700" size={20} />
              </div>
              <span className="text-sm font-medium text-emerald-700">Add Link</span>
            </Link>
            <Link to="/today" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-amber-50 hover:bg-amber-100 transition-all text-center group">
              <div className="w-10 h-10 rounded-xl bg-amber-200 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FiCalendar className="text-amber-700" size={20} />
              </div>
              <span className="text-sm font-medium text-amber-700">Today Tasks</span>
            </Link>
            <Link to="/upcoming" className="flex flex-col items-center gap-2 p-4 rounded-xl bg-purple-50 hover:bg-purple-100 transition-all text-center group">
              <div className="w-10 h-10 rounded-xl bg-purple-200 flex items-center justify-center group-hover:scale-110 transition-transform">
                <FiClock className="text-purple-700" size={20} />
              </div>
              <span className="text-sm font-medium text-purple-700">Upcoming</span>
            </Link>
          </div>
        </motion.div>

        {/* Google Drive */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
          className="glass-card p-6"
        >
          <h2 className="font-bold text-gray-800 mb-4 flex items-center gap-2">
            <span className="text-lg">☁️</span> Google Drive
          </h2>
          {user?.drive_connected ? (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 border border-emerald-200">
                <div className="w-10 h-10 rounded-full bg-emerald-100 flex items-center justify-center">
                  <FiCheckCircle className="text-emerald-600" size={22} />
                </div>
                <div>
                  <p className="font-semibold text-emerald-700">Connected</p>
                  <p className="text-sm text-emerald-600">Files auto-sync to Drive</p>
                </div>
              </div>
              <button onClick={handleDisconnectDrive} className="text-sm text-red-500 hover:text-red-600 font-medium hover:underline">
                Disconnect Drive
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-gray-500 text-sm">
                Connect Google Drive to automatically backup your learning materials and access them from anywhere.
              </p>
              <button onClick={handleConnectDrive} className="btn-secondary w-full flex items-center justify-center gap-2 text-sm">
                <FiLink2 size={16} /> Connect Google Drive
              </button>
            </div>
          )}
        </motion.div>
      </div>

      {/* Upcoming preview */}
      {stats && (stats.tomorrow > 0 || stats.future > 0) && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass-card p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-bold text-gray-800 flex items-center gap-2">
              <span className="text-lg">📆</span> Coming Up
            </h2>
            <Link to="/upcoming" className="text-sm text-primary-600 font-medium hover:underline">
              View all →
            </Link>
          </div>
          <div className="flex flex-wrap gap-4">
            {stats.tomorrow > 0 && (
              <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 rounded-xl">
                <span className="text-2xl font-bold text-blue-600">{stats.tomorrow}</span>
                <span className="text-sm text-blue-700 font-medium">tasks tomorrow</span>
              </div>
            )}
            {stats.future > 0 && (
              <div className="flex items-center gap-3 px-4 py-3 bg-purple-50 rounded-xl">
                <span className="text-2xl font-bold text-purple-600">{stats.future}</span>
                <span className="text-sm text-purple-700 font-medium">future tasks</span>
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Spaced repetition info */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
        className="mt-8 glass-card p-6"
      >
        <h2 className="font-bold text-gray-800 mb-3 flex items-center gap-2">
          <span className="text-lg">🧠</span> How Spaced Repetition Works
        </h2>
        <p className="text-gray-500 text-sm mb-4">
          Your materials are automatically scheduled for review at scientifically optimal intervals:
        </p>
        <div className="flex flex-wrap gap-3">
          {[
            { day: 'Day 1', label: 'Quick recall', color: 'bg-blue-100 text-blue-700' },
            { day: 'Day 3', label: 'Short-term', color: 'bg-indigo-100 text-indigo-700' },
            { day: 'Day 6', label: 'Medium-term', color: 'bg-purple-100 text-purple-700' },
            { day: 'Day 29', label: 'Long-term', color: 'bg-pink-100 text-pink-700' },
            { day: 'Day 179', label: 'Mastery', color: 'bg-rose-100 text-rose-700' },
          ].map((stage, i) => (
            <div key={i} className={`px-3 py-2 rounded-xl ${stage.color} text-sm font-medium`}>
              <span className="font-bold">{stage.day}</span>
              <span className="opacity-75 ml-1">- {stage.label}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
}
