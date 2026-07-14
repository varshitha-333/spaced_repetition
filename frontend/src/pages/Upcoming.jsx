import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getUpcomingRevisions } from '../services/api';
import Navbar from '../components/Navbar';

export default function Upcoming() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'today', 'week', 'month'

  useEffect(() => {
    getUpcomingRevisions()
      .then(r => {
        const arr = Array.isArray(r.data) ? r.data : (r.data?.revisions || []);
        setItems(arr);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Filter items based on selected filter
  const filteredItems = items.filter(r => {
    if (!r.scheduled_date) return false;
    const date = new Date(r.scheduled_date);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    if (filter === 'today') {
      const tomorrow = new Date(today);
      tomorrow.setDate(tomorrow.getDate() + 1);
      return date >= today && date < tomorrow;
    } else if (filter === 'week') {
      const nextWeek = new Date(today);
      nextWeek.setDate(nextWeek.getDate() + 7);
      return date >= today && date < nextWeek;
    } else if (filter === 'month') {
      const nextMonth = new Date(today);
      nextMonth.setMonth(nextMonth.getMonth() + 1);
      return date >= today && date < nextMonth;
    }
    return true;
  });

  // Group by date and limit to 5 per day
  const grouped = filteredItems.reduce((acc, r) => {
    const k = r.scheduled_date || 'Unscheduled';
    if (!acc[k]) acc[k] = [];
    if (acc[k].length < 5) acc[k].push(r);
    return acc;
  }, {});
  const days = Object.keys(grouped).sort();

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <h1 className="font-display text-3xl font-bold mb-1">What's coming up</h1>
        <p className="text-ink-muted mb-6">Your scheduled revisions — calm preview, no urgency.</p>

        {/* Date Filter */}
        <div className="flex gap-2 mb-6">
          {['all', 'today', 'week', 'month'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm font-medium capitalize ${
                filter === f 
                  ? 'bg-indigo-600 text-white' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="card p-6 shimmer h-40" />
        ) : days.length === 0 ? (
          <div className="card p-10 text-center">
            <div className="text-4xl mb-2">🌱</div>
            <div className="font-semibold">Nothing scheduled yet</div>
            <div className="text-sm text-ink-muted">Add a resource and we'll lay out the next 6 months.</div>
          </div>
        ) : (
          <div className="space-y-5">
            {days.map((d, i) => (
              <motion.div key={d} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}>
                <div className="font-display font-semibold mb-2">
                  {new Date(d).toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}
                  <span className="text-xs text-ink-muted font-normal ml-2">· {grouped[d].length} revision{grouped[d].length !== 1 && 's'}</span>
                </div>
                <div className="grid sm:grid-cols-2 gap-3">
                  {grouped[d].map(r => (
                    <div key={r.id} className="card p-4">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="pill-indigo">Day {r.stage || r.day_number}</span>
                        {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline truncate">open ↗</a>}
                        {r.supabase_url && <a href={r.supabase_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline">file ↗</a>}
                        {r.drive_link && <a href={r.drive_link} target="_blank" rel="noreferrer" className="text-xs text-emerald-600 hover:underline truncate">Drive ↗</a>}
                      </div>
                      <div className="font-semibold truncate">{r.heading || 'Untitled'}</div>
                      {r.description && <div className="text-sm text-ink-muted line-clamp-2 mt-1">{r.description}</div>}
                    </div>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
