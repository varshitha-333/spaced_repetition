import { motion } from 'framer-motion';
import { FiExternalLink, FiCheck, FiClock, FiSkipForward, FiFileText, FiLink, FiType } from 'react-icons/fi';

const stageColors = [
  'from-blue-400 to-blue-500',
  'from-indigo-400 to-indigo-500',
  'from-purple-400 to-purple-500',
  'from-pink-400 to-pink-500',
  'from-rose-400 to-rose-500',
];

const stageLabels = ['Day 1', 'Day 3', 'Day 6', 'Day 29', 'Day 179'];

export default function RevisionCard({
  revision,
  onComplete,
  onPostpone,
  onSkip,
  index = 0,
  showActions = true,
  isOverdue = false,
}) {
  const stageIndex = (revision.stage || 1) - 1;
  const stageColor = stageColors[stageIndex] || stageColors[0];
  const stageLabel = stageLabels[stageIndex] || `Stage ${revision.stage}`;
  const link = revision.drive_link || revision.supabase_url || revision.url;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.4 }}
      className={`glass-card overflow-hidden card-hover ${isOverdue ? 'border-l-4 border-l-red-400' : ''}`}
    >
      <div className="p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-800 text-lg leading-tight truncate">
              {revision.heading}
            </h3>
            {isOverdue && (
              <span className="inline-flex items-center gap-1 mt-1 text-xs font-medium text-red-500 bg-red-50 px-2 py-0.5 rounded-full">
                <FiClock size={12} /> Overdue - {revision.scheduled_date}
              </span>
            )}
          </div>
          <span className={`stage-badge bg-gradient-to-r ${stageColor} text-white shrink-0`}>
            {stageLabel}
          </span>
        </div>

        {/* Description */}
        <p className="text-gray-500 text-sm leading-relaxed mb-4 line-clamp-2">
          {revision.description}
        </p>

        {/* Progress */}
        <div className="mb-4">
          <div className="flex items-center justify-between text-xs text-gray-400 mb-1.5">
            <span>Revision progress</span>
            <span>{revision.stage}/{revision.total_stages}</span>
          </div>
          <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full bg-gradient-to-r ${stageColor}`}
              initial={{ width: 0 }}
              animate={{ width: `${(revision.stage / revision.total_stages) * 100}%` }}
              transition={{ duration: 0.8, delay: index * 0.08 + 0.3 }}
            />
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {link && (
            <a
              href={link}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-primary-600 bg-primary-50 hover:bg-primary-100 transition-all"
            >
              <FiExternalLink size={14} />
              <span>Open Material</span>
            </a>
          )}
          {showActions && (
            <>
              {onComplete && (
                <button
                  onClick={() => onComplete(revision.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-emerald-600 bg-emerald-50 hover:bg-emerald-100 transition-all"
                >
                  <FiCheck size={14} />
                  <span>Done</span>
                </button>
              )}
              {onPostpone && (
                <button
                  onClick={() => onPostpone(revision.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-amber-600 bg-amber-50 hover:bg-amber-100 transition-all"
                >
                  <FiClock size={14} />
                  <span>Tomorrow</span>
                </button>
              )}
              {onSkip && (
                <button
                  onClick={() => onSkip(revision.id)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium text-gray-500 bg-gray-50 hover:bg-gray-100 transition-all"
                >
                  <FiSkipForward size={14} />
                  <span>Skip</span>
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
