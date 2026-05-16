import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import Footer from '../components/Footer';
import { useAuth } from '../hooks/useAuth';

const tiers = [
  {
    id: 'free', name: 'Free', price: '₹0', tagline: 'For students building a habit',
    cta: 'Start free', to: '/register',
    features: [
      'Core spaced repetition flow (1·3·6·29·179)',
      'Manual daily review tracking',
      'Basic upload + AI title generation',
      'Google Drive sync',
    ],
  },
  {
    id: 'core', name: 'Core', price: '₹199', tagline: 'For consistent learners', featured: true,
    cta: 'Choose Core', to: '/register',
    features: [
      'Morning SMS reminders at 8 AM',
      'Night recap SMS at 9 PM',
      'Calmer UI with full upcoming view',
      'Drive sync visibility',
      'Concept linker (lite)',
    ],
  },
  {
    id: 'premium', name: 'Premium', price: '₹499', tagline: 'For exam season & heavy workloads',
    cta: 'Get Premium FREE 30 days', to: '/payment',
    badge: '🎁 FREE for 30 days',
    features: [
      'Everything in Core',
      'AI Smart Summary of uploads',
      'AI Flashcard generator',
      'AI Quiz Me (MCQs from your notes)',
      'AI Concept Linker (auto-group resources)',
      'Streak coach in your night SMS',
      'Priority for new AI features',
    ],
  },
];

export default function Pricing() {
  const { user } = useAuth();

  return (
    <div className="min-h-screen">
      {/* simple top bar */}
      <div className="container-page py-5 flex items-center">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white">📚</div>
          <span className="font-display font-bold text-lg">LearnFlow</span>
        </Link>
        <div className="flex-1" />
        {user
          ? <Link to="/dashboard" className="btn-secondary text-sm">Back to app</Link>
          : <Link to="/login" className="btn-secondary text-sm">Sign in</Link>}
      </div>

      <div className="container-page py-10">
        <div className="text-center mb-12">
          <span className="pill-peach mb-4">🎁 Launch offer · Premium FREE for 30 days</span>
          <h1 className="font-display text-4xl sm:text-5xl font-bold mb-3">Simple, student-friendly pricing</h1>
          <p className="text-ink-muted max-w-xl mx-auto">
            Start free. Upgrade only when you actually need the AI. Right now, Premium is on us.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-5 max-w-5xl mx-auto">
          {tiers.map((t, i) => (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.08 }}
              className={`card p-7 relative ${t.featured ? 'ring-ribbon scale-[1.02]' : ''}`}
            >
              {t.featured && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 pill-ink shadow-lift">
                  Best for most students
                </div>
              )}
              {t.badge && (
                <div className="absolute -top-3 right-4 pill-peach shadow-soft">{t.badge}</div>
              )}

              <div className={`inline-block pill ${t.id === 'free' ? 'bg-ink/90 text-white' : t.id === 'core' ? 'bg-indigo-600 text-white' : 'bg-peach-500 text-white'} mb-3`}>
                {t.name}
              </div>
              <div className="text-3xl font-bold mb-1">
                {t.price}<span className="text-base font-normal text-ink-muted">{t.id !== 'free' ? '/mo' : ''}</span>
              </div>
              <div className="text-sm text-ink-muted mb-5">{t.tagline}</div>
              <ul className="space-y-2 text-sm mb-6">
                {t.features.map(f => (
                  <li key={f} className="flex gap-2">
                    <span className="text-indigo-500 mt-0.5">✓</span>
                    <span className="text-ink-soft">{f}</span>
                  </li>
                ))}
              </ul>
              <Link
                to={t.to}
                className={t.id === 'premium' ? 'btn-peach w-full' : t.featured ? 'btn-primary w-full' : 'btn-secondary w-full'}
              >
                {t.cta}
              </Link>
            </motion.div>
          ))}
        </div>

        <div className="text-center text-xs text-ink-muted mt-8">
          Prices in INR · Cancel anytime · No card required during the 30-day launch offer.
        </div>
      </div>
      <Footer />
    </div>
  );
}
