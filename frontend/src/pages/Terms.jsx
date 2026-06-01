// src/pages/Terms.jsx
import { Link } from 'react-router-dom';
import Footer from '../components/Footer';

export default function Terms() {
  return (
    <div className="min-h-screen">
      <div className="container-page py-5 flex items-center">
        <Link to="/" className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white">📚</div>
          <span className="font-display font-bold text-lg">LearnFlow</span>
        </Link>
        <div className="flex-1" />
        <Link to="/" className="btn-ghost text-sm">Home</Link>
      </div>

      <article className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="font-display text-4xl font-bold mb-1">Terms of Service</h1>
        <p className="text-sm text-ink-muted mb-8">Last updated: June 2026</p>

        <p>By using LearnFlow you agree to these Terms.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">1. The service</h2>
        <p>LearnFlow helps students remember what they study using spaced repetition. We currently offer a Free plan, a Core plan, and a Premium plan that is free for the first 30 days via the launch coupons (LAUNCH30 / STUDENT30 / FIRST100 / LEARNFREE).</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">2. Your responsibilities</h2>
        <ul className="list-disc pl-6 space-y-1.5">
          <li>Don't upload illegal or copyrighted content (unless you have permission).</li>
          <li>Don't share your account.</li>
          <li>Don't abuse the AI features. Rate limits apply.</li>
        </ul>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">3. Payments</h2>
        <p>The current checkout is a demo / launch promotion. No real payment is captured when a launch coupon is applied. Premium activates for 30 days from coupon redemption.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">4. Cancellation</h2>
        <p>You can stop using LearnFlow any time. Email us to delete your data permanently.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">5. Liability</h2>
        <p>LearnFlow is provided "as is" without warranty of any kind. We are not liable for grades, exam outcomes, or any memory failures.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">6. Changes</h2>
        <p>We may update these Terms occasionally. We'll show the new "Last updated" date when we do.</p>

        <p className="mt-10 text-sm">
          <Link to="/" className="text-indigo-600 underline">← Back to LearnFlow</Link>{' '}
          ·{' '}
          <Link to="/privacy" className="text-indigo-600 underline">Privacy Policy</Link>
        </p>
      </article>

      <Footer />
    </div>
  );
}
