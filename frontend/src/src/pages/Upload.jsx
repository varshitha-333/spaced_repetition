import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadPreview, uploadSave } from '../utils/api';
import toast from 'react-hot-toast';
import {
  FiUpload, FiLink, FiType, FiFile, FiX, FiEye,
  FiSave, FiRefreshCw, FiCheckCircle, FiEdit3, FiZap
} from 'react-icons/fi';

export default function Upload() {
  const [mode, setMode] = useState('file'); // file | url | text
  const [file, setFile] = useState(null);
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [preview, setPreview] = useState(null);
  const [heading, setHeading] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const fileRef = useRef(null);
  const navigate = useNavigate();

  const handlePreview = async () => {
    if (mode === 'file' && !file) return toast.error('Please select a file');
    if (mode === 'url' && !url.trim()) return toast.error('Please enter a URL');
    if (mode === 'text' && !text.trim()) return toast.error('Please enter some text');

    setLoading(true);
    try {
      const fd = new FormData();
      if (mode === 'file') fd.append('file', file);
      else if (mode === 'url') fd.append('url', url);
      else fd.append('text', text);

      const res = await uploadPreview(fd);
      setPreview(res.data);
      setHeading(res.data.heading);
      setDescription(res.data.description);
      toast.success('Preview generated with AI!');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Preview failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!heading.trim()) return toast.error('Title is required');
    setSaving(true);
    try {
      await uploadSave({
        heading: heading.trim(),
        description: description.trim(),
        source: preview?.source || mode,
        url: preview?.url || (mode === 'url' ? url : null),
        supabase_path: preview?.supabase_path,
        filename: preview?.filename || file?.name,
      });
      toast.success('Saved & scheduled for review!');
      navigate('/today');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setUrl('');
    setText('');
    setPreview(null);
    setHeading('');
    setDescription('');
    if (fileRef.current) fileRef.current.value = '';
  };

  const modes = [
    { id: 'file', icon: FiFile, label: 'File Upload', desc: 'PDF, DOC, TXT' },
    { id: 'url', icon: FiLink, label: 'URL / Link', desc: 'Any webpage' },
    { id: 'text', icon: FiType, label: 'Paste Text', desc: 'Notes, content' },
  ];

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800 mb-2 flex items-center gap-3">
          <span className="text-3xl">📤</span> Add Learning Material
        </h1>
        <p className="text-gray-500 mb-8">Upload content and let AI generate a title & description for you</p>
      </motion.div>

      {/* Mode Selector */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="grid grid-cols-3 gap-3 mb-8"
      >
        {modes.map((m) => {
          const Icon = m.icon;
          const active = mode === m.id;
          return (
            <button
              key={m.id}
              onClick={() => { setMode(m.id); setPreview(null); }}
              className={`relative p-4 rounded-2xl border-2 transition-all duration-300 text-center group ${
                active
                  ? 'border-primary-400 bg-primary-50 shadow-glow'
                  : 'border-gray-200 bg-white hover:border-gray-300 hover:bg-gray-50'
              }`}
            >
              <Icon
                size={24}
                className={`mx-auto mb-2 transition-colors ${active ? 'text-primary-600' : 'text-gray-400 group-hover:text-gray-600'}`}
              />
              <p className={`text-sm font-semibold ${active ? 'text-primary-700' : 'text-gray-700'}`}>{m.label}</p>
              <p className={`text-xs mt-0.5 ${active ? 'text-primary-500' : 'text-gray-400'}`}>{m.desc}</p>
            </button>
          );
        })}
      </motion.div>

      {/* Input Area */}
      <AnimatePresence mode="wait">
        <motion.div
          key={mode}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: -20 }}
          transition={{ duration: 0.3 }}
          className="glass-card p-6 mb-6"
        >
          {mode === 'file' && (
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-3">Choose a File</label>
              <div
                onClick={() => fileRef.current?.click()}
                className={`relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-300 ${
                  file
                    ? 'border-primary-400 bg-primary-50'
                    : 'border-gray-300 hover:border-primary-300 hover:bg-primary-50/30'
                }`}
              >
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.doc,.docx,.txt,.md"
                  onChange={(e) => setFile(e.target.files[0])}
                  className="hidden"
                />
                {file ? (
                  <div className="flex items-center justify-center gap-3">
                    <FiCheckCircle className="text-primary-500" size={24} />
                    <div>
                      <p className="font-semibold text-primary-700">{file.name}</p>
                      <p className="text-sm text-primary-500">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button onClick={(e) => { e.stopPropagation(); setFile(null); if(fileRef.current) fileRef.current.value=''; }} className="ml-3 p-1 rounded-full hover:bg-primary-100">
                      <FiX className="text-primary-500" />
                    </button>
                  </div>
                ) : (
                  <div>
                    <FiUpload className="mx-auto text-gray-400 mb-3" size={32} />
                    <p className="text-gray-600 font-medium">Click to upload or drag & drop</p>
                    <p className="text-gray-400 text-sm mt-1">PDF, DOC, DOCX, TXT, MD (max 50MB)</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {mode === 'url' && (
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2">Enter URL</label>
              <div className="relative">
                <FiLink className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="url"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="input-field pl-11"
                  placeholder="https://example.com/article"
                />
              </div>
              <p className="text-xs text-gray-400 mt-2">We'll extract content from the page automatically</p>
            </div>
          )}

          {mode === 'text' && (
            <div>
              <label className="block text-sm font-medium text-gray-600 mb-2">Paste Your Notes</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                className="input-field min-h-[160px] resize-y"
                placeholder="Paste your notes, lecture content, or any text here..."
              />
              <p className="text-xs text-gray-400 mt-2">{text.length} characters</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={handlePreview}
              disabled={loading}
              className="btn-primary flex-1 flex items-center justify-center gap-2"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <FiZap size={16} />
                  <span>Generate Preview with AI</span>
                </>
              )}
            </button>
            {(file || url || text) && (
              <button onClick={resetForm} className="btn-secondary px-4">
                <FiRefreshCw size={16} />
              </button>
            )}
          </div>
        </motion.div>
      </AnimatePresence>

      {/* Preview */}
      <AnimatePresence>
        {preview && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="glass-card p-6 border-2 border-primary-200"
          >
            <div className="flex items-center gap-2 mb-5">
              <FiEye className="text-primary-500" />
              <h2 className="text-lg font-bold text-gray-800">Preview & Edit</h2>
              <span className="ml-auto text-xs bg-primary-100 text-primary-600 px-2 py-1 rounded-full font-medium">AI Generated</span>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5 flex items-center gap-1.5">
                  <FiEdit3 size={14} /> Title
                </label>
                <input
                  type="text"
                  value={heading}
                  onChange={(e) => setHeading(e.target.value)}
                  className="input-field font-semibold"
                  placeholder="Enter a title"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-600 mb-1.5 flex items-center gap-1.5">
                  <FiEdit3 size={14} /> Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="input-field min-h-[100px] resize-y"
                  placeholder="Enter a description"
                />
              </div>

              {preview.content_snippet && (
                <div className="p-4 bg-gray-50 rounded-xl border border-gray-100">
                  <p className="text-xs font-medium text-gray-400 mb-1">Content Preview</p>
                  <p className="text-sm text-gray-600 line-clamp-3">{preview.content_snippet}</p>
                </div>
              )}

              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn-success flex-1 flex items-center justify-center gap-2"
                >
                  {saving ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <FiSave size={16} />
                      <span>Save & Schedule Reviews</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setPreview(null)}
                  className="btn-secondary px-6 flex items-center justify-center gap-2"
                >
                  <FiX size={16} />
                  <span>Cancel</span>
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
