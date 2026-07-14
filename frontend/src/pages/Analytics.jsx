import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getAnalyticsOverview, getRevisionProgress, getTodayAnalytics, getStreakAnalytics, getCompletionHistory, getSmsStatus } from '../services/api';
import Navbar from '../components/Navbar';

export default function Analytics() {
  const [overview, setOverview] = useState(null);
  const [progress, setProgress] = useState(null);
  const [today, setToday] = useState(null);
  const [streak, setStreak] = useState(null);
  const [history, setHistory] = useState(null);
  const [smsStatus, setSmsStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    try {
      const [overviewRes, progressRes, todayRes, streakRes, historyRes, smsRes] = await Promise.all([
        getAnalyticsOverview().catch(e => ({ data: null })),
        getRevisionProgress().catch(e => ({ data: null })),
        getTodayAnalytics().catch(e => ({ data: null })),
        getStreakAnalytics().catch(e => ({ data: null })),
        getCompletionHistory().catch(e => ({ data: null })),
        getSmsStatus().catch(e => ({ data: null }))
      ]);
      
      setOverview(overviewRes.data);
      setProgress(progressRes.data);
      setToday(todayRes.data);
      setStreak(streakRes.data);
      setHistory(historyRes.data);
      setSmsStatus(smsRes.data);
    } catch (err) {
      console.error('Failed to load analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-8">
          <div className="card p-6 shimmer h-64" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="font-display text-3xl font-bold mb-2">Analytics Dashboard</h1>
          <p className="text-ink-muted mb-6">Track your learning progress and revision habits</p>
        </motion.div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 card-quiet p-1 w-fit overflow-x-auto">
          {[
            { k: 'overview', l: '📊 Overview' },
            { k: 'progress', l: '📈 Progress' },
            { k: 'streak', l: '🔥 Streak' },
            { k: 'history', l: '📅 History' },
            { k: 'sms', l: '📱 SMS Status' },
          ].map(t => (
            <button key={t.k} onClick={() => setActiveTab(t.k)}
              className={`px-3 py-1.5 rounded-lg text-sm transition whitespace-nowrap ${activeTab === t.k ? 'bg-white shadow-soft text-ink font-semibold' : 'text-ink-soft hover:text-ink'}`}>
              {t.l}
            </button>
          ))}
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              <StatCard title="Study Materials" value={overview?.total_study_materials || 0} icon="📚" />
              <StatCard title="Revisions" value={overview?.total_revision_materials || 0} icon="🔄" />
              <StatCard title="AI Materials" value={overview?.total_ai_materials || 0} icon="🤖" />
              <StatCard title="Flashcards" value={overview?.total_flashcards || 0} icon="🃏" />
              <StatCard title="Quiz Questions" value={overview?.total_quiz_questions || 0} icon="❓" />
              <StatCard title="Mindmaps" value={overview?.total_mindmaps || 0} icon="🗺️" />
              <StatCard title="Keywords" value={overview?.total_keywords || 0} icon="🔑" />
              <StatCard title="Summaries" value={overview?.total_summaries || 0} icon="📝" />
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard title="Completed" value={overview?.total_completed_revisions || 0} icon="✅" color="emerald" />
              <StatCard title="Pending" value={overview?.total_pending_revisions || 0} icon="⏳" color="amber" />
              <StatCard title="Missed" value={overview?.total_missed_revisions || 0} icon="❌" color="red" />
              <StatCard title="Upcoming" value={overview?.total_upcoming_revisions || 0} icon="📅" color="blue" />
            </div>

            <div className="card p-6">
              <h3 className="font-semibold mb-4">Current Streak</h3>
              <div className="flex items-center gap-4">
                <div className="text-5xl">🔥</div>
                <div>
                  <div className="text-3xl font-bold">{streak?.current_streak || 0} days</div>
                  <div className="text-sm text-ink-muted">Keep the momentum going!</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Progress Tab */}
        {activeTab === 'progress' && (
          <div className="space-y-4">
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Overall Completion</h3>
              <div className="flex items-center gap-4">
                <div className="flex-1">
                  <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-indigo-500 to-purple-500 transition-all duration-500"
                      style={{ width: `${progress?.overall_completion || 0}%` }}
                    />
                  </div>
                </div>
                <div className="text-2xl font-bold">{progress?.overall_completion || 0}%</div>
              </div>
              <div className="text-sm text-ink-muted mt-2">
                {progress?.remaining || 0}% remaining
              </div>
            </div>

            <div className="card p-6">
              <h3 className="font-semibold mb-4">Spaced Repetition Progress</h3>
              <div className="space-y-4">
                {progress?.by_stage && Object.entries(progress.by_stage).map(([stage, data]) => (
                  <div key={stage} className="flex items-center gap-4">
                    <div className="w-24 text-sm font-medium">{stage.replace('_', ' ')}</div>
                    <div className="flex-1">
                      <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
                        <div 
                          className={`h-full transition-all duration-500 ${data.completed === data.total ? 'bg-emerald-500' : 'bg-indigo-500'}`}
                          style={{ width: `${data.completion_percent}%` }}
                        />
                      </div>
                    </div>
                    <div className="w-20 text-right text-sm">
                      {data.completed}/{data.total}
                    </div>
                    <div className="w-16 text-right text-sm font-medium">
                      {data.completion_percent}%
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Streak Tab */}
        {activeTab === 'streak' && (
          <div className="space-y-4">
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Learning Streak</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <StatCard title="Current Streak" value={`${streak?.current_streak || 0} days`} icon="🔥" />
                <StatCard title="Longest Streak" value={`${streak?.longest_streak || 0} days`} icon="🏆" />
                <StatCard title="Days Studied" value={streak?.days_studied || 0} icon="📚" />
                <StatCard title="Days Missed" value={streak?.days_missed || 0} icon="😴" />
              </div>
            </div>

            <div className="card p-6">
              <h3 className="font-semibold mb-4">Consistency Score</h3>
              <div className="flex items-center gap-4">
                <div className="text-5xl">📊</div>
                <div>
                  <div className="text-3xl font-bold">{streak?.consistency_score || 0}/100</div>
                  <div className="text-sm text-ink-muted">
                    {streak?.consistency_score >= 80 ? 'Excellent consistency!' : 
                     streak?.consistency_score >= 60 ? 'Good consistency!' : 
                     'Room for improvement'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="space-y-4">
            <div className="card p-6">
              <h3 className="font-semibold mb-4">Daily Completion History (Last 30 Days)</h3>
              <div className="h-64 flex items-end gap-1">
                {history?.daily_history?.map((day, i) => (
                  <div 
                    key={i}
                    className="flex-1 bg-indigo-500 hover:bg-indigo-600 transition-colors rounded-t"
                    style={{ height: `${Math.max(5, (day.count / 10) * 100)}%` }}
                    title={`${day.date}: ${day.count} revisions`}
                  />
                ))}
              </div>
              <div className="flex justify-between text-xs text-ink-muted mt-2">
                <span>30 days ago</span>
                <span>Today</span>
              </div>
            </div>
          </div>
        )}

        {/* SMS Status Tab */}
        {activeTab === 'sms' && (
          <div className="space-y-4">
            <div className="card p-6">
              <h3 className="font-semibold mb-4">SMS Reminder Status</h3>
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-ink-muted">Phone Number</span>
                  <span className="font-medium">{smsStatus?.phone_number || 'Not set'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-ink-muted">SMS Enabled</span>
                  <span className={`font-medium ${smsStatus?.sms_enabled ? 'text-emerald-600' : 'text-red-600'}`}>
                    {smsStatus?.sms_enabled ? '✅ Yes' : '❌ No'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-ink-muted">Last Reminder Sent</span>
                  <span className="font-medium">{smsStatus?.last_reminder_sent || 'Never'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-ink-muted">Total SMS Sent</span>
                  <span className="font-medium">{smsStatus?.total_sms_sent || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ title, value, icon, color = 'indigo' }) {
  const colorClasses = {
    indigo: 'bg-indigo-50 text-indigo-700',
    emerald: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    red: 'bg-red-50 text-red-700',
    blue: 'bg-blue-50 text-blue-700',
  };

  return (
    <div className={`${colorClasses[color]} p-4 rounded-lg`}>
      <div className="text-2xl mb-1">{icon}</div>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-sm opacity-80">{title}</div>
    </div>
  );
}
