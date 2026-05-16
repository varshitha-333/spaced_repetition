import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getUpcomingRevisions } from '../utils/api';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';
import { format, parseISO, isToday, isTomorrow, differenceInDays } from 'date-fns';
import { FiCalendar, FiExternalLink, FiClock } from 'react-icons/fi';

const stageColors = [
  'bg-blue-100 text-blue-700',
  'bg-indigo-100 text-indigo-700',
  'bg-purple-100 text-purple-700',
  'bg-pink-100 text-pink-700',
  'bg-rose-100 text-rose-700',
];

function formatDateLabel(dateStr) {
  const d = parseISO(dateStr);
  if (isToday(d)) return 'Today';
  if (isTomorrow(d)) return 'Tomorrow';
  const diff = differenceInDays(d, new Date());
  if (diff <= 7) return `In ${diff} days`;
  return format(d, 'EEEE, MMM d');
}

export default function Upcoming() {
  const [data, setData] = useState({ grouped: {}, total: 0 });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUpcoming();
  }, []);

  const fetchUpcoming = async () => {
    try {
      const res = await getUpcomingRevisions();
      setData(res.data);
    } catch {
      toast.error('Failed to load upcoming tasks');
    } finally {
      setLoading(false);
    }
  };

  const sortedDates = Object.keys(data.grouped).sort();

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 bg-gray-200 rounded-xl" />
          {[1,2,3].map(i => <div key={i} className="h-24 bg-gray-100 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 flex items-center gap-3">
          <span className="text-3xl">📆</span> Upcoming Reviews
        </h1>
        <p className="text-gray-500 mt-1">
          {data.total} task{data.total !== 1 ? 's' : ''} scheduled
        </p>
      </motion.div>

      {data.total === 0 ? (
        <EmptyState
          emoji="📚"
          title="No upcoming reviews"
          description="Upload learning materials to get started with spaced repetition."
          linkTo="/upload"
          linkLabel="Upload Material"
        />
      ) : (
        <div className="space-y-6">
          {sortedDates.map((dateStr, dateIdx) => {
            const revisions = data.grouped[dateStr];
            const label = formatDateLabel(dateStr);
            const diff = differenceInDays(parseISO(dateStr), new Date());
            const isNear = diff <= 2;

            return (
              <motion.div
                key={dateStr}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: dateIdx * 0.1 }}
              >
                {/* Date Header */}
                <div className={`flex items-center gap-3 mb-3 px-1`}>
                  <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                    isNear ? 'bg-amber-100' : 'bg-primary-50'
                  }`}>
                    <FiCalendar className={isNear ? 'text-amber-600' : 'text-primary-500'} size={18} />
                  </div>
                  <div>
                    <h2 className="font-bold text-gray-800">{label}</h2>
                    <p className="text-xs text-gray-400">{format(parseISO(dateStr), 'EEEE, MMMM d, yyyy')}</p>
                  </div>
                  <span className={`ml-auto px-3 py-1 rounded-full text-sm font-bold ${
                    isNear ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {revisions.length}
                  </span>
                </div>

                {/* Revision List */}
                <div className="space-y-2 pl-4 sm:pl-6 border-l-2 border-gray-100 ml-5">
                  {revisions.map((rev, idx) => {
                    const stg = (rev.stage || 1) - 1;
                    const link = rev.drive_link || rev.supabase_url || rev.url;

                    return (
                      <motion.div
                        key={rev.id}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: dateIdx * 0.1 + idx * 0.05 }}
                        className="glass-card p-4 hover:shadow-md transition-all"
                      >
                        <div className="flex items-start gap-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="font-semibold text-gray-800 text-sm truncate">
                                {rev.heading}
                              </h3>
                              <span className={`stage-badge ${stageColors[stg] || stageColors[0]}`}>
                                Stage {rev.stage}
                              </span>
                            </div>
                            <p className="text-gray-400 text-xs mt-1 line-clamp-1">{rev.description}</p>
                          </div>
                          {link && (
                            <a
                              href={link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="shrink-0 p-2 rounded-lg text-primary-500 hover:bg-primary-50 transition"
                            >
                              <FiExternalLink size={16} />
                            </a>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
