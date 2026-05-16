import { motion } from 'framer-motion';

export default function StatsCard({ icon, label, value, color = 'primary', delay = 0, subtitle }) {
  const colors = {
    primary: 'from-primary-400 to-primary-600',
    success: 'from-emerald-400 to-emerald-600',
    warning: 'from-amber-400 to-orange-500',
    danger: 'from-red-400 to-red-500',
    purple: 'from-purple-400 to-purple-600',
    blue: 'from-blue-400 to-cyan-500',
  };

  const bgColors = {
    primary: 'bg-primary-50',
    success: 'bg-emerald-50',
    warning: 'bg-amber-50',
    danger: 'bg-red-50',
    purple: 'bg-purple-50',
    blue: 'bg-blue-50',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4 }}
      className="glass-card p-5 card-hover"
    >
      <div className="flex items-center gap-4">
        <div className={`w-12 h-12 rounded-2xl ${bgColors[color]} flex items-center justify-center text-xl shrink-0`}>
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-2xl font-bold text-gray-800">{value}</p>
          <p className="text-sm text-gray-500 truncate">{label}</p>
          {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
        </div>
      </div>
    </motion.div>
  );
}
