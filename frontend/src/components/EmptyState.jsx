import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';

export default function EmptyState({ emoji = '🎉', title, description, linkTo, linkLabel }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="flex flex-col items-center justify-center py-16 px-6 text-center"
    >
      <motion.span
        className="text-7xl mb-4 block"
        animate={{ y: [0, -8, 0] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      >
        {emoji}
      </motion.span>
      <h3 className="text-xl font-bold text-gray-700 mb-2">{title}</h3>
      <p className="text-gray-400 max-w-sm mb-6">{description}</p>
      {linkTo && (
        <Link to={linkTo} className="btn-primary text-sm">
          {linkLabel || 'Get Started'}
        </Link>
      )}
    </motion.div>
  );
}
