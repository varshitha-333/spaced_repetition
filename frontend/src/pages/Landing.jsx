import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { getTopReviews } from '../services/api';
import Footer from '../components/Footer';

const features = [
  { icon: '🧠', title: 'Spaced repetition that fits you',
    desc: 'Day 1, 3, 6, 29, 179 intervals — calibrated by science, surfaced calmly.' },
  { icon: '📥', title: 'Drop in anything',
    desc: 'PDFs, links, plain text. AI titles and descriptions appear automatically.' },
  { icon: '✨', title: 'AI study superpowers (Premium)',
    desc: 'Smart summaries, flashcards, quiz mode, concept links — built on Gemini.' },
  { icon: '📱', title: 'Gentle SMS nudges',
    desc: '8 AM "what to revise" + 9 PM "how today went". One button to enable.' },
  { icon: '🔥', title: 'Streaks that stay kind',
    desc: 'No guilt-shaming. Just a coach that celebrates progress, however small.' },
  { icon: '🔒', title: 'Your data, your Drive',
    desc: 'Sync to your own Google Drive. You own everything. Privacy by default.' },
];

const steps = [
  { n: 1, t: 'Drop in a note, PDF, or link', s: 'AI names it. AI describes it. No copy-paste of metadata.' },
  { n: 2, t: 'LearnFlow schedules 5 revisions', s: 'Spread across 6 months — invisible, automatic.' },
  { n: 3, t: 'Open the app each morning', s: 'See exactly what to revise today. Nothing more.' },
  { n: 4, t: 'Mark complete, watch streak grow', s: 'The system handles the rest — for the next 179 days.' },
];

export default function Landing() {
  const [reviews, setReviews] = useState([]);

  useEffect(() => {
    getTopReviews().then(r => setReviews(r.data?.reviews || [])).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen overflow-x-hidden">
      {/* ─────────── Top bar ─────────── */}
      <nav className="absolute top-0 left-0 right-0 z-30">
        <div className="container-page py-5 flex items-center">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white text-lg shadow-soft">📚</div>
            <span className="font-display font-bold text-xl">LearnFlow</span>
          </Link>
          <div className="flex-1" />
          <div className="hidden md:flex items-center gap-2">
            <Link to="/pricing" className="btn-ghost text-sm">Pricing</Link>
            <Link to="/login" className="btn-ghost text-sm">Sign in</Link>
            <Link to="/register" className="btn-primary text-sm">Get started free</Link>
          </div>
          <Link to="/login" className="md:hidden btn-secondary text-sm">Sign in</Link>
        </div>
      </nav>

      {/* ─────────── Hero ─────────── */}
      <section className="relative pt-32 pb-20">
        <div className="absolute inset-0 bg-hero-glow pointer-events-none" />
        <div className="container-page relative">
          <motion.div
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
            className="text-center max-w-3xl mx-auto"
          >
            <span className="pill bg-white/80 border border-indigo-100 text-indigo-700 mb-5">
              🎁 Launch offer · Premium FREE for 30 days
            </span>
            <h1 className="font-display text-5xl sm:text-6xl font-bold leading-tight mb-5">
              Remember what you <span className="text-gradient">actually</span> studied.
            </h1>
            <p className="text-lg text-ink-muted leading-relaxed mb-8">
              LearnFlow is a calm, AI-powered spaced repetition app for students.
              Drop in notes, get nudged at the right moment, and watch knowledge stick — for months, not minutes.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-3">
              <Link to="/register" className="btn-primary text-base !py-3 !px-6">
                Try Premium FREE · 30 days
              </Link>
              <Link to="/pricing" className="btn-secondary text-base !py-3 !px-6">
                See pricing
              </Link>
            </div>
            <div className="mt-6 text-xs text-ink-muted">
              No card. No tricks. Cancel anytime — but you probably won't.
            </div>
          </motion.div>

          {/* Floating preview cards */}
          <div className="mt-16 grid md:grid-cols-3 gap-4 max-w-4xl mx-auto">
            {[
              { tag: 'Morning · 8:00', title: 'Revise: Photosynthesis (Day 6)', body: 'Light reactions → ATP + NADPH → Calvin cycle uses both to fix CO₂.', tone: 'indigo' },
              { tag: 'Streak', title: '🔥 14 days in a row', body: 'You\'re in the top 8% of students this week.', tone: 'peach' },
              { tag: 'Premium AI', title: 'Smart summary generated', body: '5 bullet points · 2 flashcards · 1 quiz ready.', tone: 'sage' },
            ].map((c, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 + i * 0.15, duration: 0.5 }}
                className="card card-hover p-5 animate-float"
                style={{ animationDelay: `${i * 0.8}s` }}
              >
                <div className={`pill-${c.tone === 'indigo' ? 'indigo' : c.tone === 'peach' ? 'peach' : 'sage'} mb-3`}>{c.tag}</div>
                <div className="font-semibold mb-1">{c.title}</div>
                <div className="text-sm text-ink-muted">{c.body}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── How it works ─────────── */}
      <section className="py-20">
        <div className="container-page">
          <div className="text-center mb-12">
            <h2 className="font-display text-3xl sm:text-4xl font-bold mb-3">How LearnFlow works in 30 seconds</h2>
            <p className="text-ink-muted">Four small steps. Then the system carries you for half a year.</p>
          </div>
          <div className="grid md:grid-cols-4 gap-5">
            {steps.map((s, i) => (
              <motion.div
                key={s.n}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="card p-6 card-hover"
              >
                <div className="w-9 h-9 rounded-lg bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center mb-3">
                  {s.n}
                </div>
                <div className="font-semibold mb-1.5">{s.t}</div>
                <div className="text-sm text-ink-muted">{s.s}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── Features grid ─────────── */}
      <section className="py-16">
        <div className="container-page">
          <div className="text-center mb-10">
            <h2 className="font-display text-3xl sm:text-4xl font-bold mb-3">Everything a student actually needs</h2>
            <p className="text-ink-muted">Calm by default. Powerful when you tap in.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={f.title}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.05 }}
                className="card p-6 card-hover"
              >
                <div className="text-3xl mb-3">{f.icon}</div>
                <div className="font-semibold mb-1.5">{f.title}</div>
                <div className="text-sm text-ink-muted leading-relaxed">{f.desc}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ─────────── Premium CTA strip ─────────── */}
      <section className="py-12">
        <div className="container-page">
          <motion.div
            initial={{ opacity: 0, scale: 0.97 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
            className="premium-ribbon rounded-3xl p-8 sm:p-12 text-white shadow-lift relative overflow-hidden"
          >
            <div className="absolute -top-10 -right-10 w-48 h-48 rounded-full bg-white/10 animate-float" />
            <div className="absolute -bottom-12 -left-8 w-40 h-40 rounded-full bg-white/10 animate-float" style={{ animationDelay: '1.2s' }} />
            <div className="relative grid md:grid-cols-2 gap-6 items-center">
              <div>
                <div className="pill bg-white/20 text-white mb-3">Limited · First 30 days</div>
                <h3 className="font-display text-3xl sm:text-4xl font-bold mb-3 leading-tight">
                  Get Premium <span className="underline decoration-wavy decoration-2 underline-offset-4">free</span>.
                  All AI features unlocked.
                </h3>
                <p className="opacity-90 mb-2">
                  Use code <code className="bg-white/20 px-2 py-0.5 rounded">LAUNCH30</code> (or any of {' '}
                  <code className="bg-white/20 px-2 py-0.5 rounded">STUDENT30</code>,{' '}
                  <code className="bg-white/20 px-2 py-0.5 rounded">FIRST100</code>,{' '}
                  <code className="bg-white/20 px-2 py-0.5 rounded">LEARNFREE</code>) at checkout.
                </p>
              </div>
              <div className="flex md:justify-end">
                <Link to="/register" className="bg-white text-indigo-700 font-semibold rounded-xl px-6 py-3 hover:bg-white/95 shadow-lift">
                  Claim 30 days free →
                </Link>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ─────────── Top reviews ─────────── */}
      <section className="py-16">
        <div className="container-page">
          <div className="text-center mb-10">
            <h2 className="font-display text-3xl sm:text-4xl font-bold mb-3">What students are saying</h2>
            <p className="text-ink-muted">Top reviews — ranked by our Gemini-powered quality score.</p>
          </div>
          {reviews.length === 0 ? (
            <div className="card p-8 text-center text-ink-muted max-w-2xl mx-auto">
              Be the first to leave a review — once you've used LearnFlow for a week,
              your story could appear here.
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {reviews.map((r, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 16 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.06 }}
                  className="card p-5"
                >
                  <div className="flex gap-1 mb-2 text-peach-500">
                    {'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}
                  </div>
                  <div className="text-sm text-ink leading-relaxed mb-3">"{r.text}"</div>
                  <div className="text-xs text-ink-muted font-medium">— {r.name}</div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ─────────── Final CTA ─────────── */}
      <section className="py-16">
        <div className="container-page text-center">
          <h2 className="font-display text-3xl sm:text-4xl font-bold mb-4">
            Start remembering. Stop re-reading.
          </h2>
          <p className="text-ink-muted mb-6 max-w-xl mx-auto">
            Join the launch — Premium is on us for 30 days. Then ₹0 forever on Free, or ₹199 on Core.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link to="/register" className="btn-peach !py-3 !px-6">Try Premium free</Link>
            <Link to="/pricing" className="btn-secondary !py-3 !px-6">Compare plans</Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
