import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { motion } from 'framer-motion';
import { uploadPreview, uploadSave, aiAutoProcess, getPremiumStatus } from '../services/api';
import Navbar from '../components/Navbar';

export default function Upload() {
  const nav = useNavigate();
  const [mode, setMode] = useState('file');
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState('');
  const [premium, setPremium] = useState(null);

  useEffect(() => {
    getPremiumStatus().then(r => setPremium(r.data)).catch(() => {});
  }, []);

  const runPreview = async () => {
    const fd = new FormData();
    if (mode === 'file' && file) fd.append('file', file);
    else if (mode === 'url' && url) fd.append('url', url);
    else if (mode === 'text' && text.trim()) fd.append('text', text);
    else { toast.error('Add something first'); return; }
    
    setBusy(true);
    setUploadProgress(0);
    setProcessingStatus('Uploading...');
    
    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) {
            clearInterval(progressInterval);
            return 90;
          }
          return prev + 10;
        });
      }, 100);

      const r = await uploadPreview(fd);
      clearInterval(progressInterval);
      setUploadProgress(100);
      setProcessingStatus('Processing...');
      setPreview(r.data);
      setProcessingStatus('');
      toast.success('Preview generated successfully');
    } catch (e) {
      setUploadProgress(0);
      setProcessingStatus('');
      const msg = e.response?.data?.error || e.message || 'Preview failed';
      toast.error(msg);
    } finally { 
      setBusy(false); 
    }
  };

  const save = async () => {
    if (!preview) return;
    setBusy(true);
    setProcessingStatus('Saving...');
    
    try {
      const r = await uploadSave(preview);
      const learning_id = r.data?.learning_id;
      toast.success('Saved — revisions scheduled 🎯');

      // NEW: if user is Premium, kick off the AI auto-process (markdown +
      // mindmap + summary + flashcards) in the background. The result is
      // saved on the learning row and surfaced inside AI Lab automatically.
      if (premium?.is_premium && learning_id) {
        setProcessingStatus('Running AI auto-process...');
        toast('✨ Running AI auto-process in the background…', { duration: 3500 });
        aiAutoProcess(learning_id)
          .then(() => {
            setProcessingStatus('');
            toast.success('AI Lab assets ready for this upload');
          })
          .catch(() => {
            setProcessingStatus('');
            // silent — user can still trigger it from AI Lab
          });
      }

      setTimeout(() => nav('/dashboard'), premium?.is_premium ? 2000 : 500);
    } catch (e) {
      setProcessingStatus('');
      const msg = e.response?.data?.error || 'Save failed';
      toast.error(msg);
    } finally { 
      setBusy(false); 
    }
  };

  return (
    <div className="min-h-screen">
      <Navbar />
      <div className="container-tight py-8">
        <motion.h1 initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
          className="font-display text-3xl font-bold mb-2">Add a new resource</motion.h1>
        <p className="text-ink-muted mb-6">Drop in anything. AI titles + descriptions it for you.</p>

        {premium?.is_premium && (
          <div className="card-quiet p-3 mb-4 text-sm border border-peach-200 bg-peach-50/50">
            ✨ <b>Premium auto-process is ON.</b> After you save, we'll automatically
            generate a Markdown version, a mind-map, a 5-bullet summary, and 6
            flashcards — ready in your AI Lab and on your next revision day.
          </div>
        )}

        <div className="card-quiet inline-flex p-1 mb-5">
          {[
            { k: 'file', l: '📄 File' },
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
              <input type="file" className="hidden" onChange={e => setFile(e.target.files?.[0] || null)} accept=".pdf,.docx,.doc,.ppt,.pptx,.txt,.md,.jpg,.jpeg,.png,.gif,.bmp,.webp" />
              <div className="text-4xl mb-2">📄</div>
              <div className="font-semibold">{file?.name || 'Click to choose a file'}</div>
              <div className="text-xs text-ink-muted mt-1">PDF · DOCX · PPT · TXT · Images</div>
            </label>
          )}
          {mode === 'url' && (
            <input className="input" placeholder="https://…" value={url} onChange={e => setUrl(e.target.value)} />
          )}
          {mode === 'text' && (
            <textarea rows={6} className="input" placeholder="Paste your notes here…"
              value={text} onChange={e => setText(e.target.value)} />
          )}

          {/* Upload Progress */}
          {uploadProgress > 0 && uploadProgress < 100 && (
            <div className="mt-4">
              <div className="flex justify-between text-xs text-ink-muted mb-1">
                <span>{processingStatus}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div className="bg-indigo-600 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
              </div>
            </div>
          )}

          <button onClick={runPreview} disabled={busy} className="btn-primary mt-4">
            {busy ? 'Processing…' : '✨ Generate AI title & description'}
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
            
            {/* Processing Status */}
            {processingStatus && (
              <div className="mb-4 p-3 bg-indigo-50 rounded-lg text-sm text-indigo-700">
                {processingStatus}
              </div>
            )}
            
            <div className="flex gap-2">
              <button onClick={save} disabled={busy} className="btn-primary">
                {busy ? 'Saving…' : 'Save & schedule revisions'}
              </button>
              <button onClick={() => setPreview(null)} disabled={busy} className="btn-secondary">Discard</button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
