import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getUpcomingRevisions } from '../services/api';
import Navbar from '../components/Navbar';

export default function Upcoming() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getUpcomingRevisions()
      .then(r => setItems(r.data?.revisions || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  // Group by date
  const grouped = items.reduce((acc, r) => {
    const k = r.scheduled_date || 'Unscheduled';
    (acc[k] = acc[k] || []).push(r);
    return acc;
  }, {});
  const days = Object.keys(grouped).sort();

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <h1 className="font-display text-3xl font-bold mb-1">What's coming up</h1>
        <p className="text-ink-muted mb-6">Your scheduled revisions — calm preview, no urgency.</p>

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
                      <div className="flex items-center gap-2 mb-1">
                        <span className="pill-indigo">Day {r.day_number}</span>
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
