import { useEffect, useState } from 'react';
import { getAdminMetrics } from '../services/api';
import Navbar from '../components/Navbar';

export default function AdminDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadMetrics();
    const interval = setInterval(loadMetrics, 30000); // Refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const loadMetrics = async () => {
    try {
      const res = await getAdminMetrics();
      setMetrics(res.data);
      setError(null);
    } catch (err) {
      setError('Failed to load metrics');
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

  if (error) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-8">
          <div className="card p-10 text-center">
            <div className="text-4xl mb-2">⚠️</div>
            <div className="font-semibold">Error loading dashboard</div>
            <div className="text-sm text-ink-muted">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <h1 className="font-display text-3xl font-bold mb-1">Admin Dashboard</h1>
        <p className="text-ink-muted mb-6">System monitoring and metrics</p>

        {/* Cron Job Status */}
        <div className="card p-6 mb-4">
          <h2 className="font-semibold text-lg mb-4">Cron Job Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-indigo-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-indigo-700">{metrics?.cron?.last_execution ? '✅' : '❌'}</div>
              <div className="text-sm text-indigo-600">Last Execution</div>
              <div className="text-xs text-ink-muted mt-1">{metrics?.cron?.last_execution || 'Never'}</div>
            </div>
            <div className="bg-emerald-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-emerald-700">{metrics?.cron?.successful || 0}</div>
              <div className="text-sm text-emerald-600">Successful Jobs</div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-red-700">{metrics?.cron?.failed || 0}</div>
              <div className="text-sm text-red-600">Failed Jobs</div>
            </div>
            <div className="bg-amber-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-amber-700">{metrics?.cron?.retried || 0}</div>
              <div className="text-sm text-amber-600">Retried Jobs</div>
            </div>
          </div>
        </div>

        {/* SMS Status */}
        <div className="card p-6 mb-4">
          <h2 className="font-semibold text-lg mb-4">SMS Notifications</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-blue-700">{metrics?.sms?.sent || 0}</div>
              <div className="text-sm text-blue-600">SMS Sent</div>
            </div>
            <div className="bg-red-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-red-700">{metrics?.sms?.failed || 0}</div>
              <div className="text-sm text-red-600">SMS Failed</div>
            </div>
            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-purple-700">{metrics?.sms?.pending || 0}</div>
              <div className="text-sm text-purple-600">Pending</div>
            </div>
          </div>
        </div>

        {/* Queue Status */}
        <div className="card p-6 mb-4">
          <h2 className="font-semibold text-lg mb-4">Queue Status</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-cyan-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-cyan-700">{metrics?.queue?.length || 0}</div>
              <div className="text-sm text-cyan-600">Queue Length</div>
            </div>
            <div className="bg-orange-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-orange-700">{metrics?.queue?.processing || 0}</div>
              <div className="text-sm text-orange-600">Processing</div>
            </div>
            <div className="bg-pink-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-pink-700">{metrics?.dead_letter?.count || 0}</div>
              <div className="text-sm text-pink-600">Dead Letter</div>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div className="card p-6 mb-4">
          <h2 className="font-semibold text-lg mb-4">Performance</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-teal-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-teal-700">{metrics?.performance?.avg_response_time || 0}ms</div>
              <div className="text-sm text-teal-600">Avg Response Time</div>
            </div>
            <div className="bg-lime-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-lime-700">{metrics?.performance?.p95_response_time || 0}ms</div>
              <div className="text-sm text-lime-600">P95 Response Time</div>
            </div>
            <div className="bg-violet-50 p-4 rounded-lg">
              <div className="text-2xl font-bold text-violet-700">{metrics?.performance?.requests_per_minute || 0}</div>
              <div className="text-sm text-violet-600">Requests/Min</div>
            </div>
          </div>
        </div>

        {/* Recent Errors */}
        <div className="card p-6">
          <h2 className="font-semibold text-lg mb-4">Recent Errors</h2>
          {metrics?.errors?.length > 0 ? (
            <div className="space-y-2">
              {metrics.errors.slice(0, 5).map((err, i) => (
                <div key={i} className="bg-red-50 p-3 rounded-lg text-sm">
                  <div className="font-semibold text-red-700">{err.type}</div>
                  <div className="text-red-600">{err.message}</div>
                  <div className="text-xs text-ink-muted mt-1">{err.timestamp}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center text-ink-muted py-4">No recent errors</div>
          )}
        </div>
      </div>
    </div>
  );
}
