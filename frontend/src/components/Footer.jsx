import { Link } from 'react-router-dom';

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-white/60 bg-white/40 backdrop-blur-md">
      <div className="container-page py-10 grid md:grid-cols-3 gap-8 text-sm">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-peach-400 flex items-center justify-center text-white">📚</div>
            <span className="font-display font-bold text-lg">LearnFlow</span>
          </div>
          <p className="text-ink-muted leading-relaxed">
            Spaced repetition that finally feels calm. Built for students who want to remember what they learn — not just collect notes.
          </p>
        </div>
        <div>
          <div className="font-semibold mb-3">Product</div>
          <ul className="space-y-1.5 text-ink-soft">
            <li><Link to="/" className="hover:text-indigo-600">Home</Link></li>
            <li><Link to="/pricing" className="hover:text-indigo-600">Pricing</Link></li>
            <li><Link to="/register" className="hover:text-indigo-600">Get started free</Link></li>
          </ul>
        </div>
        <div>
          <div className="font-semibold mb-3">Launch offer 🎁</div>
          <p className="text-ink-muted mb-3">Premium is free for the first 30 days. Use any of these codes at checkout:</p>
          <div className="flex flex-wrap gap-1.5">
            {['LAUNCH30', 'STUDENT30', 'FIRST100', 'LEARNFREE'].map(c => (
              <code key={c} className="text-xs bg-indigo-50 text-indigo-700 px-2 py-1 rounded">{c}</code>
            ))}
          </div>
        </div>
      </div>
      <div className="text-center text-xs text-ink-muted py-4 border-t border-white/60">
        © {new Date().getFullYear()} LearnFlow · Made with care for students.
      </div>
    </footer>
  );
}
