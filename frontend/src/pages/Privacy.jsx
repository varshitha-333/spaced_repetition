// src/pages/Privacy.jsx
// ────────────────────────────────────────────────────────────────────────
// PUBLIC privacy-policy page — required for Google OAuth verification.
// Rules Google enforces (these are the exact items that failed verification):
//   ✓ Hosted on a domain you own  (you must add your own domain to Vercel)
//   ✓ Visible WITHOUT a login
//   ✓ Linked from your homepage (Landing.jsx footer link points here)
//   ✓ Domain matches the homepage URL on the consent screen
// ────────────────────────────────────────────────────────────────────────
import { Link } from 'react-router-dom';
import Footer from '../components/Footer';

export default function Privacy() {
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

      <article className="max-w-3xl mx-auto px-6 py-10 prose prose-indigo">
        <h1 className="font-display text-4xl font-bold mb-1">Privacy Policy</h1>
        <p className="text-sm text-ink-muted mb-8">Last updated: June 2026</p>

        <p>
          LearnFlow ("we", "us") is a spaced-repetition study app for students.
          This policy explains exactly what data we collect, why, and how you can
          control it.
        </p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">1. What we collect</h2>
        <ul className="list-disc pl-6 space-y-1.5">
          <li><b>Account info</b> — username, email, password (bcrypt-hashed). Created when you register.</li>
          <li><b>Learning content</b> — titles, descriptions, and any PDFs / text you upload. Stored in Supabase Storage.</li>
          <li><b>Optional Google Drive</b> — with your explicit consent we sync your uploads into a folder called <em>Learning Intake</em> in <b>your own</b> Drive. We request only the <code>drive.file</code> scope, which restricts us to files we create. We <b>cannot</b> read your other Drive files.</li>
          <li><b>Optional phone number</b> — only saved if you enable SMS reminders. Used to send 8 AM + 9 PM nudges via Twilio.</li>
        </ul>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">2. Why we ask for Google access</h2>
        <ul className="list-disc pl-6 space-y-1.5">
          <li><code>openid</code>, <code>userinfo.email</code>, <code>userinfo.profile</code> — to let you sign in with Google.</li>
          <li><code>drive.file</code> — to upload <em>your</em> study materials into a folder in <em>your</em> Drive.</li>
          <li><code>spreadsheets</code> — to maintain one LearnFlow log spreadsheet in your Drive.</li>
        </ul>
        <p>
          We do <b>not</b> share Google user data with any third party except as
          required to provide the feature (i.e. Google APIs themselves). We do
          not use it for advertising. We do not train ML models on it.
        </p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">3. How we use your data</h2>
        <ul className="list-disc pl-6 space-y-1.5">
          <li>Schedule revisions on the Day 1 / 3 / 6 / 29 / 179 intervals.</li>
          <li>Send SMS reminders (only if you turn them on).</li>
          <li>Call Google Gemini for AI summaries / flashcards / quizzes when you press those buttons (Premium feature).</li>
        </ul>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">4. Data deletion</h2>
        <p>
          Email <a href="mailto:learnflow.app@gmail.com" className="text-indigo-600 underline">learnflow.app@gmail.com</a>{' '}
          and we delete your account, files, and Drive credentials within 7 days. You can also disconnect Google Drive
          any time from <em>Profile → Google Drive → Disconnect</em>.
        </p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">5. Security</h2>
        <p>Passwords are bcrypt-hashed. Auth uses JWT (HS256, 30-day expiry). Drive credentials are stored in our Supabase database with row-level security.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">6. Children</h2>
        <p>LearnFlow is intended for students 13 and older. We do not knowingly collect data from children under 13.</p>

        <h2 className="font-display text-2xl font-bold mt-8 mb-2">7. Contact</h2>
        <p>
          Questions: <a href="mailto:learnflow.app@gmail.com" className="text-indigo-600 underline">learnflow.app@gmail.com</a>
        </p>

        <p className="mt-10 text-sm">
          <Link to="/" className="text-indigo-600 underline">← Back to LearnFlow</Link>{' '}
          ·{' '}
          <Link to="/terms" className="text-indigo-600 underline">Terms of Service</Link>
        </p>
      </article>

      <Footer />
    </div>
  );
}
