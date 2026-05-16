import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { getLearnings } from '../utils/api';
import EmptyState from '../components/EmptyState';
import toast from 'react-hot-toast';
import { FiExternalLink, FiFile, FiLink, FiType, FiClock } from 'react-icons/fi';

const sourceIcons = {
  file: { icon: FiFile, color: 'text-blue-500 bg-blue-50' },
  url: { icon: FiLink, color: 'text-emerald-500 bg-emerald-50' },
  text: { icon: FiType, color: 'text-purple-500 bg-purple-50' },
};

export default function History() {
  const [learnings, setLearnings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLearnings();
  }, []);

  const fetchLearnings = async () => {
    try {
      const res = await getLearnings();
      setLearnings(res.data);
    } catch {
      toast.error('Failed to load history');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 bg-gray-200 rounded-xl" />
          {[1,2,3,4].map(i => <div key={i} className="h-20 bg-gray-100 rounded-2xl" />)}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 flex items-center gap-3">
          <span className="text-3xl">📖</span> Learning History
        </h1>
        <p className="text-gray-500 mt-1">{learnings.length} item{learnings.length !== 1 ? 's' : ''} saved</p>
      </motion.div>

      {learnings.length === 0 ? (
        <EmptyState
          emoji="📝"
          title="No learning history"
          description="Start adding materials to build your learning library."
          linkTo="/upload"
          linkLabel="Upload Material"
        />
      ) : (
        <div className="space-y-3">
          {learnings.map((item, idx) => {
            const src = sourceIcons[item.source_type] || sourceIcons.text;
            const Icon = src.icon;
            const link = item.drive_link || item.url;
            const date = item.created_at ? new Date(item.created_at).toLocaleDateString('en-US', {
              month: 'short', day: 'numeric', year: 'numeric'
            }) : '';

            return (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="glass-card p-4 sm:p-5 card-hover"
              >
                <div className="flex items-start gap-3 sm:gap-4">
                  <div className={`w-10 h-10 rounded-xl ${src.color} flex items-center justify-center shrink-0`}>
                    <Icon size={20} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-gray-800 text-sm sm:text-base truncate">
                        {item.title}
                      </h3>
                      {link && (
                        <a
                          href={link}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="shrink-0 p-1.5 rounded-lg text-primary-500 hover:bg-primary-50 transition"
                        >
                          <FiExternalLink size={16} />
                        </a>
                      )}
                    </div>
                    <p className="text-gray-400 text-xs sm:text-sm mt-0.5 line-clamp-2">{item.content}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                      <span className="flex items-center gap-1">
                        <FiClock size={12} />
                        {date}
                      </span>
                      <span className="capitalize px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 font-medium">
                        {item.source_type}
                      </span>
                      {item.revision_stage && (
                        <span className="px-2 py-0.5 rounded-full bg-primary-50 text-primary-600 font-medium">
                          Stage {item.revision_stage}/5
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
