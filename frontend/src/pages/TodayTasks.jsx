import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getTodayRevisions, getOverdueRevisions, getCompletedRevisions, completeRevision, postponeRevision, skipRevision, getRevisionStats } from '../utils/api';
import RevisionCard from '../components/RevisionCard';
import StatsCard from '../components/StatsCard';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';

export default function TodayTasks() {
  const [today, setToday] = useState([]);
  const [overdue, setOverdue] = useState([]);
  const [completed, setCompleted] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('today');

  useEffect(() => {
    fetchAll();
  }, []);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [tRes, oRes, cRes, sRes] = await Promise.all([
        getTodayRevisions(),
        getOverdueRevisions(),
        getCompletedRevisions(),
        getRevisionStats(),
      ]);
      setToday(tRes.data);
      setOverdue(oRes.data);
      setCompleted(cRes.data);
      setStats(sRes.data);
    } catch {
      toast.error('Failed to load tasks');
    } finally {
      setLoading(false);
    }
  };

  const handleComplete = async (id) => {
    try {
      await completeRevision(id);
      toast.success('Great job! Revision completed! 🎉');
      fetchAll();
    } catch {
      toast.error('Failed to complete');
    }
  };

  const handlePostpone = async (id) => {
    try {
      await postponeRevision(id);
      toast.success('Moved to tomorrow');
      fetchAll();
    } catch {
      toast.error('Failed to postpone');
    }
  };

  const handleSkip = async (id) => {
    try {
      await skipRevision(id);
      toast.success('Skipped for now');
      fetchAll();
    } catch {
      toast.error('Failed to skip');
    }
  };

  const tabs = [
    { id: 'today', label: 'Today', count: today.length, emoji: '📅' },
    { id: 'overdue', label: 'Overdue', count: overdue.length, emoji: '⚠️' },
    { id: 'completed', label: 'Done', count: completed.length, emoji: '✅' },
  ];

  const currentItems = activeTab === 'today' ? today : activeTab === 'overdue' ? overdue : completed;

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-64 bg-gray-200 rounded-xl" />
          <div className="grid md:grid-cols-3 gap-4">
            {[1,2,3].map(i => <div key={i} className="h-32 bg-gray-100 rounded-2xl" />)}
          </div>
          {[1,2].map(i => <div key={i} className="h-48 bg-gray-100 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 flex items-center gap-3">
          <span className="text-3xl">📋</span> Today's Tasks
        </h1>
        <p className="text-gray-500 mt-1">
          {new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
        </p>
      </motion.div>

      {/* Mini Stats */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          <StatsCard icon="📅" label="Due Today" value={stats.today} color="primary" delay={0.05} />
          <StatsCard icon="⚠️" label="Overdue" value={stats.overdue} color={stats.overdue > 0 ? 'danger' : 'success'} delay={0.1} />
          <StatsCard icon="✅" label="Done Today" value={stats.completed_today} color="success" delay={0.15} />
          <StatsCard icon="🔥" label="Streak" value={`${stats.streak}d`} color="warning" delay={0.2} />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all duration-300 ${
              activeTab === tab.id
                ? 'bg-primary-500 text-white shadow-glow'
                : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
            }`}
          >
            <span>{tab.emoji}</span>
            <span>{tab.label}</span>
            {tab.count > 0 && (
              <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                activeTab === tab.id ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-600'
              }`}>
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Content */}
      {currentItems.length === 0 ? (
        <EmptyState
          emoji={activeTab === 'completed' ? '🎉' : '✨'}
          title={
            activeTab === 'today' ? 'No tasks for today!'
            : activeTab === 'overdue' ? 'All caught up!'
            : 'No completed tasks yet'
          }
          description={
            activeTab === 'today' ? 'You\'re all caught up! Upload new materials to start your learning journey.'
            : activeTab === 'overdue' ? 'Great job keeping up with your reviews!'
            : 'Complete some reviews to see them here.'
          }
          linkTo={activeTab === 'completed' ? undefined : '/upload'}
          linkLabel="Upload Material"
        />
      ) : (
        <div className="grid md:grid-cols-2 gap-4">
          {currentItems.map((rev, idx) => (
            <RevisionCard
              key={rev.id}
              revision={rev}
              index={idx}
              isOverdue={activeTab === 'overdue'}
              showActions={activeTab !== 'completed'}
              onComplete={activeTab !== 'completed' ? handleComplete : undefined}
              onPostpone={activeTab !== 'completed' ? handlePostpone : undefined}
              onSkip={activeTab !== 'completed' ? handleSkip : undefined}
            />
          ))}
        </div>
      )}
    </div>
  );
}
