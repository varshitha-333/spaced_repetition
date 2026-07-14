import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { getCompletedRevisions } from '../services/api';
import Navbar from '../components/Navbar';

export default function History() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getCompletedRevisions().then(r => {
      const arr = Array.isArray(r.data) ? r.data : (r.data?.revisions || []);
      setItems(arr);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <h1 className="font-display text-3xl font-bold mb-1">Your history</h1>
        <p className="text-ink-muted mb-6">Everything you've revised. Quiet receipts of progress. ✨</p>

        {loading ? (
          <div className="card p-6 shimmer h-40" />
        ) : items.length === 0 ? (
          <div className="card p-10 text-center">
            <div className="text-4xl mb-2">📜</div>
            <div className="font-semibold">No completed revisions yet</div>
            <div className="text-sm text-ink-muted">Your first ✓ will show here.</div>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {items.map((r, i) => (
              <motion.div 
                key={r.id} 
                initial={{ opacity: 0, y: 6 }} 
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="card p-4"
              >
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="pill-sage">✓ Day {r.stage || r.day_number}</span>
                  {(r.completed_date || r.completed_at) && (
                    <span className="text-xs text-ink-muted">
                      {new Date(r.completed_date || r.completed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <div className="font-semibold truncate">{r.heading || 'Untitled'}</div>
                {r.description && <div className="text-sm text-ink-muted line-clamp-2 mt-1">{r.description}</div>}
                
                {/* Links */}
                <div className="flex flex-wrap gap-2 mt-2">
                  {r.url && (
                    <a href={r.url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline">
                      Source ↗
                    </a>
                  )}
                  {r.supabase_url && (
                    <a href={r.supabase_url} target="_blank" rel="noreferrer" className="text-xs text-indigo-600 hover:underline">
                      File ↗
                    </a>
                  )}
                  {r.drive_link && (
                    <a href={r.drive_link} target="_blank" rel="noreferrer" className="text-xs text-emerald-600 hover:underline">
                      Drive ↗
                    </a>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
