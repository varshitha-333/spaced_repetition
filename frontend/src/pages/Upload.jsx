import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { uploadPreview, uploadSave } from '../services/api';
import Navbar from '../components/Navbar';

export default function Upload() {
  const nav = useNavigate();
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);

  const runPreview = async () => {
    const fd = new FormData();
    if (mode === 'file' && file) fd.append('file', file);
    else if (mode === 'url' && url) fd.append('url', url);
    else if (mode === 'text' && text.trim()) fd.append('text', text);
    else { toast.error('Add something first'); return; }
    setBusy(true);
    try {
      const r = await uploadPreview(fd);
      setPreview(r.data);
    } catch (e) { toast.error('Preview failed'); }
    finally { setBusy(false); }
  };

  const save = async () => {
    if (!preview) return;
    setBusy(true);
    try {
      await uploadSave(preview);
      toast.success('Saved — revisions scheduled 🎯');
      nav('/dashboard');
    } catch { toast.error('Save failed'); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <motion.h1 initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          className="font-display text-3xl font-bold mb-2">Add a new resource</motion.h1>
        <p className="text-ink-muted mb-6">Drop in anything. AI titles + descriptions it for you.</p>

        <div className="card-quiet inline-flex p-1 mb-5">
          {[
            { k: 'file', l: '📄 File / PDF' },
            { k: 'url',  l: '🔗 Link' },
            { k: 'text', l: '✏️ Paste text' },
          ].map(t => (
            <button key={t.k} onClick={() => setMode(t.k)}
              className={`px-3 py-1.5 text-sm rounded-lg transition ${mode === t.k ? 'bg-white shadow-soft font-semibold' : 'text-ink-soft'}`}>
              {t.l}
            </button>
          ))}
        </div>

        <div className="card p-6">
          {mode === 'file' && (
            <label className="block border-2 border-dashed border-indigo-200 rounded-2xl p-10 text-center cursor-pointer hover:border-indigo-400 transition">
              <input type="file" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} accept=".pdf,.docx,.txt,.md" />
              <div className="text-4xl mb-2">📄</div>
              <div className="font-semibold">{file?.name || 'Click to choose a file'}</div>
              <div className="text-xs text-ink-muted mt-1">PDF · DOCX · TXT · MD</div>
            </label>
          )}
          {mode === 'url' && (
            <input className="input" placeholder="https://…" value={url} onChange={e => setUrl(e.target.value)} />
          )}
          {mode === 'text' && (
            <textarea rows={6} className="input" placeholder="Paste your notes here…"
              value={text} onChange={e => setText(e.target.value)} />
          )}

          <button onClick={runPreview} disabled={busy} className="btn-primary mt-4">
            {busy ? '…' : '✨ Generate AI title & description'}
          </button>
        </div>

        {preview && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
            className="card p-6 mt-5">
            <div className="pill-indigo mb-3">AI preview</div>
            <input className="input mb-3 font-semibold" value={preview.heading || ''}
              onChange={e => setPreview({ ...preview, heading: e.target.value })} />
            <textarea rows={3} className="input mb-4" value={preview.description || ''}
              onChange={e => setPreview({ ...preview, description: e.target.value })} />
            <div className="flex gap-2">
              <button onClick={save} disabled={busy} className="btn-primary">
                {busy ? '…' : 'Save & schedule revisions'}
              </button>
              <button onClick={() => setPreview(null)} className="btn-secondary">Discard</button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
