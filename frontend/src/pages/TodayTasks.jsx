import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import {
  getTodayRevisions, completeRevision, postponeRevision, skipRevision,
} from '../services/api';
import Navbar from '../components/Navbar';

export default function TodayTasks() {
  const [items, setItems] = useState([]);
  const [idx, setIdx] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    getTodayRevisions().then(r => {
      // Accept both shapes — { revisions: [...] } (new) and bare array (legacy)
      const arr = Array.isArray(r.data) ? r.data : (r.data?.revisions || []);
      // Limit to first 5 items
      setItems(arr.slice(0, 5));
      setIdx(0);
    }).catch(() => {
      toast.error('Failed to load revisions');
    }).finally(() => {
      setLoading(false);
    });
  }, []);
  useEffect(load, [load]);

  const current = items[idx];
  const advance = () => setIdx(i => i + 1);

  const act = async (fn, msg) => {
    if (!current) return;
    setBusy(true);
    try { await fn(current.id); toast.success(msg); advance(); }
    catch { toast.error('Failed'); }
    finally { setBusy(false); }
  };

  if (loading) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-16 text-center">
          <div className="card p-8 shimmer h-64" />
        </div>
      </div>
    );
  }

  if (!current) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-16 text-center">
          <div className="text-6xl mb-3 animate-pop">🌿</div>
          <h1 className="font-display text-3xl font-bold">All done for today.</h1>
          <p className="text-ink-muted mt-2 mb-6">That's the whole point. Go live a little.</p>
          <Link to="/dashboard" className="btn-primary">Back to dashboard</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <div className="text-sm text-ink-muted mb-2">Focus mode · {idx + 1} of {items.length}</div>
        <motion.div key={current.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
          className="card p-8">
          <div className="pill-indigo mb-3">Day {current.stage || current.day_number || '?'}</div>
          <h2 className="font-display text-2xl font-bold mb-2">{current.heading || 'Untitled'}</h2>
          {current.description && <p className="text-ink-muted leading-relaxed">{current.description}</p>}
          
          {/* Links */}
          <div className="flex flex-wrap gap-3 mt-4">
            {current.url && (
              <a href={current.url} target="_blank" rel="noreferrer"
                className="inline-block text-indigo-600 font-medium hover:underline text-sm">
                Open source ↗
              </a>
            )}
            {current.supabase_url && (
              <a href={current.supabase_url} target="_blank" rel="noreferrer"
                className="inline-block text-indigo-600 font-medium hover:underline text-sm">
                Open file ↗
              </a>
            )}
            {current.drive_link && (
              <a href={current.drive_link} target="_blank" rel="noreferrer"
                className="inline-block text-emerald-600 font-medium hover:underline text-sm">
                Open Drive ↗
              </a>
            )}
          </div>

          <div className="grid grid-cols-3 gap-2 mt-6">
            <button disabled={busy} onClick={() => act(completeRevision, 'Locked in 🎯')} className="btn-primary">✓ Done</button>
            <button disabled={busy} onClick={() => act(postponeRevision, 'Pushed to tomorrow')} className="btn-secondary">⏭️ Later</button>
            <button disabled={busy} onClick={() => act(skipRevision, 'Skipped')} className="btn-ghost">✕ Skip</button>
          </div>
        </motion.div>

        {/* progress */}
        <div className="mt-5 h-2 bg-white/60 rounded-full overflow-hidden">
          <div className="h-full bg-gradient-to-r from-indigo-500 to-peach-400 transition-all"
            style={{ width: `${((idx) / items.length) * 100}%` }} />
        </div>
      </div>
    </div>
  );
}
