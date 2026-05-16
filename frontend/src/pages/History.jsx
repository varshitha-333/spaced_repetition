import { useEffect, useState } from 'react';
import { getCompletedRevisions } from '../services/api';
import Navbar from '../components/Navbar';

export default function History() {
  const [items, setItems] = useState([]);
  useEffect(() => { getCompletedRevisions().then(r => setItems(r.data?.revisions || [])).catch(() => {}); }, []);
  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <h1 className="font-display text-3xl font-bold mb-1">Your history</h1>
        <p className="text-ink-muted mb-6">Everything you've revised. Quiet receipts of progress. ✨</p>
        {items.length === 0 ? (
          <div className="card p-10 text-center">
            <div className="text-4xl mb-2">📜</div>
            <div className="font-semibold">No completed revisions yet</div>
            <div className="text-sm text-ink-muted">Your first ✓ will show here.</div>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3">
            {items.map(r => (
              <div key={r.id} className="card p-4">
                <div className="flex items-center gap-2 mb-1">
                  <span className="pill-sage">✓ Day {r.day_number}</span>
                  {r.completed_at && (
                    <span className="text-xs text-ink-muted">
                      {new Date(r.completed_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
                <div className="font-semibold truncate">{r.heading || 'Untitled'}</div>
                {r.description && <div className="text-sm text-ink-muted line-clamp-2 mt-1">{r.description}</div>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
