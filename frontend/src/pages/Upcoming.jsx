import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { getUpcomingRevisions } from '../utils/api';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';
import { format, parseISO, isToday, isTomorrow, differenceInDays } from 'date-fns';
import {
  FiCalendar,
  FiExternalLink,
  FiChevronDown,
  FiChevronRight,
  FiClock,
  FiLayers,
} from 'react-icons/fi';

const stageColors = [
  'bg-blue-100 text-blue-700',
  'bg-indigo-100 text-indigo-700',
  'bg-purple-100 text-purple-700',
  'bg-pink-100 text-pink-700',
  'bg-rose-100 text-rose-700',
];

const previewLimit = 2;

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
  const [expandedDates, setExpandedDates] = useState({});

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

  const sortedDates = useMemo(() => Object.keys(data.grouped).sort(), [data.grouped]);

  useEffect(() => {
    if (!sortedDates.length) return;
    setExpandedDates((current) => {
      if (Object.keys(current).length) return current;
      return { [sortedDates[0]]: true };
    });
  }, [sortedDates]);

  const toggleDate = (dateKey) => {
    setExpandedDates((current) => ({
      ...current,
      [dateKey]: !current[dateKey],
    }));
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 bg-gray-200 rounded-xl" />
          {[1, 2, 3].map((i) => <div key={i} className="h-24 bg-gray-100 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <div className="rounded-[28px] border border-white/60 bg-white/75 backdrop-blur-xl p-6 sm:p-7 shadow-soft">
          <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 flex items-center gap-3">
                <span className="text-3xl">📆</span> Upcoming Reviews
              </h1>
              <p className="text-gray-500 mt-2 max-w-2xl">
                This page now keeps the list calmer by collapsing each day into an accordion. You only expand the dates you want, instead of seeing every task at once.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:min-w-[250px]">
              <div className="rounded-2xl bg-primary-50 border border-primary-100 p-4">
                <p className="text-xs uppercase tracking-wide text-primary-500 font-semibold mb-1">Scheduled</p>
                <p className="text-2xl font-bold text-primary-700">{data.total}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 border border-slate-100 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500 font-semibold mb-1">Days</p>
                <p className="text-2xl font-bold text-slate-700">{sortedDates.length}</p>
              </div>
            </div>
          </div>
        </div>
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
        <div className="space-y-4">
          {sortedDates.map((dateStr, dateIdx) => {
            const revisions = data.grouped[dateStr];
            const label = formatDateLabel(dateStr);
            const diff = differenceInDays(parseISO(dateStr), new Date());
            const isNear = diff <= 2;
            const expanded = Boolean(expandedDates[dateStr]);
            const visibleItems = expanded ? revisions : revisions.slice(0, previewLimit);
            const hiddenCount = Math.max(revisions.length - previewLimit, 0);

            return (
              <motion.div
                key={dateStr}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: dateIdx * 0.08 }}
                className="glass-card overflow-hidden"
              >
                <button
                  onClick={() => toggleDate(dateStr)}
                  className="w-full text-left p-5 sm:p-6 hover:bg-white/40 transition-all"
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${isNear ? 'bg-amber-100' : 'bg-primary-50'}`}>
                      <FiCalendar className={isNear ? 'text-amber-600' : 'text-primary-500'} size={20} />
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                        <h2 className="font-bold text-gray-800 text-lg">{label}</h2>
                        <span className={`inline-flex w-fit items-center gap-2 px-3 py-1 rounded-full text-xs font-bold ${isNear ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-600'}`}>
                          <FiLayers size={12} /> {revisions.length} task{revisions.length !== 1 ? 's' : ''}
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mt-1">{format(parseISO(dateStr), 'EEEE, MMMM d, yyyy')}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-3 text-xs text-gray-500">
                        <span className="inline-flex items-center gap-1 rounded-full bg-slate-100 px-3 py-1">
                          <FiClock size={12} /> {expanded ? 'Expanded view' : `Compact view${hiddenCount > 0 ? ` · ${hiddenCount} hidden` : ''}`}
                        </span>
                        {!expanded && hiddenCount > 0 && (
                          <span className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-3 py-1 text-primary-600 font-semibold">
                            Click arrow to reveal all tasks
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="w-10 h-10 rounded-xl bg-gray-50 border border-gray-100 flex items-center justify-center text-gray-600 shrink-0">
                      {expanded ? <FiChevronDown size={18} /> : <FiChevronRight size={18} />}
                    </div>
                  </div>
                </button>

                <AnimatePresence initial={false}>
                  <motion.div
                    key={`${dateStr}-${expanded ? 'open' : 'closed'}`}
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22 }}
                    className="overflow-hidden"
                  >
                    <div className="px-5 sm:px-6 pb-5 sm:pb-6 border-t border-white/70 bg-gradient-to-b from-white/30 to-transparent">
                      <div className="space-y-3 pt-4">
                        {visibleItems.map((rev, idx) => {
                          const stg = (rev.stage || 1) - 1;
                          const link = rev.drive_link || rev.supabase_url || rev.url;

                          return (
                            <motion.div
                              key={rev.id}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: idx * 0.04 }}
                              className="rounded-2xl border border-white/70 bg-white/75 p-4 shadow-sm hover:shadow-md transition-all"
                            >
                              <div className="flex items-start gap-3">
                                <div className="flex-1 min-w-0">
                                  <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                    <h3 className="font-semibold text-gray-800 text-sm sm:text-base truncate">
                                      {rev.heading}
                                    </h3>
                                    <span className={`stage-badge ${stageColors[stg] || stageColors[0]}`}>
                                      Stage {rev.stage}
                                    </span>
                                  </div>
                                  <p className="text-gray-500 text-sm line-clamp-2">{rev.description}</p>
                                </div>
                                {link && (
                                  <a
                                    href={link}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="shrink-0 p-2.5 rounded-xl text-primary-500 hover:bg-primary-50 transition"
                                    title="Open revision material"
                                  >
                                    <FiExternalLink size={16} />
                                  </a>
                                )}
                              </div>
                            </motion.div>
                          );
                        })}

                        {!expanded && hiddenCount > 0 && (
                          <button
                            onClick={() => toggleDate(dateStr)}
                            className="w-full rounded-2xl border border-dashed border-primary-200 bg-primary-50/50 px-4 py-3 text-sm font-semibold text-primary-600 hover:bg-primary-50 transition-all"
                          >
                            Show {hiddenCount} more task{hiddenCount !== 1 ? 's' : ''}
                          </button>
                        )}
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
