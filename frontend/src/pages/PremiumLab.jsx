import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import toast from 'react-hot-toast';
import {
  getPremiumStatus, aiSummary, aiFlashcards, aiQuiz, aiConcepts, getLearnings,
} from '../services/api';
import Navbar from '../components/Navbar';

const tools = [
  { k: 'summary',    icon: '📝', title: 'Smart Summary',     desc: '5 memorable bullets from any note.' },
  { k: 'flashcards', icon: '🃏', title: 'Flashcard Generator', desc: '6 Q&A cards you can review forever.' },
  { k: 'quiz',       icon: '🎯', title: 'Quiz Me',            desc: '5 MCQs with explanations.' },
  { k: 'concepts',   icon: '🕸️', title: 'Concept Linker',     desc: 'Groups your saved resources.' },
];

export default function PremiumLab() {
  const [premium, setPremium] = useState(null);
  const [tool, setTool] = useState('summary');
  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [titles, setTitles] = useState([]);

  useEffect(() => {
    getPremiumStatus().then(r => setPremium(r.data));
    getLearnings().then(r => {
      const ts = (r.data?.learnings || []).map(l => l.heading || l.title).filter(Boolean);
      setTitles(ts);
    }).catch(() => {});
  }, []);

  const run = async () => {
    setResult(null);
    setLoading(true);
    try {
      if (tool === 'concepts') {
        if (titles.length === 0) { toast.error('Save some resources first'); setLoading(false); return; }
        const r = await aiConcepts(titles);
        setResult({ type: 'concepts', data: r.data?.clusters || [] });
      } else {
        if (text.trim().length < 30) { toast.error('Paste at least a paragraph (30+ chars)'); setLoading(false); return; }
        const r = tool === 'summary' ? await aiSummary(text)
                : tool === 'flashcards' ? await aiFlashcards(text)
                : await aiQuiz(text);
        setResult({
          type: tool,
          data: tool === 'summary' ? r.data?.summary : tool === 'flashcards' ? r.data?.flashcards : r.data?.quiz,
        });
      }
    } catch (e) {
      if (e.response?.status === 402) toast.error('Premium required — claim 30 days free!');
      else toast.error('AI call failed');
    } finally { setLoading(false); }
  };

  if (premium && !premium.is_premium) {
    return (
      <div className="min-h-screen">
        <Navbar />
        <div className="container-tight py-16">
          <div className="card p-10 text-center">
            <div className="text-5xl mb-3">🔒</div>
            <h1 className="font-display text-3xl font-bold mb-2">AI Lab is a Premium feature</h1>
            <p className="text-ink-muted mb-5">Right now Premium is <b>free for 30 days</b>. Just enter a coupon at checkout.</p>
            <Link to="/payment" className="btn-peach !py-3 !px-6">Claim Premium FREE →</Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <div className="flex items-end justify-between gap-3 mb-6">
          <div>
            <div className="pill-peach mb-2">✨ Premium · AI Lab</div>
            <h1 className="font-display text-3xl font-bold">Study faster with AI</h1>
            <p className="text-ink-muted text-sm">Paste any material → instant summary, flashcards, quiz, or concept map.</p>
          </div>
        </div>

        {/* Tool tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
          {tools.map(t => (
            <button key={t.k} onClick={() => { setTool(t.k); setResult(null); }}
              className={`text-left p-4 rounded-2xl border transition ${
                tool === t.k ? 'bg-white border-indigo-300 shadow-soft' : 'bg-white/60 border-white/60 hover:bg-white/90'
              }`}>
              <div className="text-2xl mb-1">{t.icon}</div>
              <div className="font-semibold text-sm">{t.title}</div>
              <div className="text-xs text-ink-muted">{t.desc}</div>
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="card p-5 mb-5">
          {tool === 'concepts' ? (
            <div>
              <div className="font-semibold mb-1">Concept Linker</div>
              <p className="text-sm text-ink-muted mb-3">
                Group all your saved resources ({titles.length}) into concept clusters using Gemini.
              </p>
            </div>
          ) : (
            <>
              <div className="label mb-1">Paste your study material</div>
              <textarea
                rows={7} className="input font-mono text-sm"
                placeholder="Paste notes, a paragraph from a textbook, or a chapter outline…"
                value={text} onChange={e => setText(e.target.value)}
              />
            </>
          )}
          <button onClick={run} disabled={loading} className="btn-primary mt-4">
            {loading ? '🪄 Generating…' : `Run ${tools.find(t => t.k === tool).title}`}
          </button>
        </div>

        {/* Result */}
        {result && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="card p-5">
            {result.type === 'summary' && (
              <pre className="whitespace-pre-wrap text-sm leading-relaxed">{result.data}</pre>
            )}

            {result.type === 'flashcards' && (
              <div className="grid sm:grid-cols-2 gap-3">
                {result.data.map((c, i) => <Flashcard key={i} q={c.q} a={c.a} />)}
              </div>
            )}

            {result.type === 'quiz' && (
              <div className="space-y-4">
                {result.data.map((q, i) => <Quiz q={q} key={i} idx={i + 1} />)}
              </div>
            )}

            {result.type === 'concepts' && (
              <div className="grid sm:grid-cols-2 gap-3">
                {result.data.map((c, i) => (
                  <div key={i} className="card-quiet p-4">
                    <div className="font-semibold text-indigo-700 mb-2">🧩 {c.concept}</div>
                    <ul className="text-sm space-y-1">
                      {(c.items || []).map((it, j) => <li key={j} className="text-ink-soft">• {it}</li>)}
                    </ul>
                  </div>
                ))}
              </div>
            )}
          </motion.div>
        )}
      </div>
    </div>
  );
}

function Flashcard({ q, a }) {
  const [flipped, setFlipped] = useState(false);
  return (
    <button onClick={() => setFlipped(f => !f)}
      className="text-left card-quiet p-4 min-h-[100px] hover:bg-white transition">
      <div className="text-xs text-ink-muted mb-1">{flipped ? 'Answer' : 'Question'} · tap to flip</div>
      <div className="font-medium">{flipped ? a : q}</div>
    </button>
  );
}

function Quiz({ q, idx }) {
  const [picked, setPicked] = useState(null);
  return (
    <div className="card-quiet p-4">
      <div className="font-semibold mb-2">{idx}. {q.q}</div>
      <div className="grid grid-cols-1 gap-2">
        {q.options.map((opt, i) => {
          const isPicked = picked === i;
          const isAnswer = q.answer_index === i;
          let cls = 'text-left text-sm px-3 py-2 rounded-lg border transition';
          if (picked === null) cls += ' bg-white hover:bg-indigo-50 border-indigo-100';
          else if (isAnswer) cls += ' bg-emerald-50 border-emerald-300 text-emerald-800';
          else if (isPicked) cls += ' bg-rose-50 border-rose-300 text-rose-800';
          else cls += ' bg-white border-indigo-100 opacity-60';
          return (
            <button key={i} disabled={picked !== null} onClick={() => setPicked(i)} className={cls}>
              {String.fromCharCode(65 + i)}. {opt}
            </button>
          );
        })}
      </div>
      {picked !== null && q.why && (
        <div className="text-xs text-ink-muted mt-3 bg-white/60 p-2 rounded">💡 {q.why}</div>
      )}
    </div>
  );
}
