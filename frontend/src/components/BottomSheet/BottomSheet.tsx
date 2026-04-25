import { useState, useRef } from 'react';
import { useIngestionStore } from '../../stores/ingestionStore';

type InputType = 'text' | 'link' | 'file' | 'folder' | 'audio';

interface BottomSheetProps {
  open: boolean;
  onClose: () => void;
}

const INPUT_OPTIONS: { type: InputType; icon: string; label: string; desc: string; accept?: string }[] = [
  { type: 'text', icon: '✏️', label: 'Text', desc: 'Paste notes, articles, or raw text' },
  { type: 'link', icon: '🔗', label: 'Link', desc: 'URL or YouTube video' },
  { type: 'file', icon: '📄', label: 'File', desc: 'PDF, DOCX, TXT, Markdown', accept: '.pdf,.docx,.txt,.md' },
  { type: 'folder', icon: '📁', label: 'Folder', desc: 'ZIP of a folder or second brain export', accept: '.zip' },
  { type: 'audio', icon: '🎧', label: 'Audio', desc: 'MP3, WAV, M4A — transcribed via Whisper', accept: '.mp3,.mp4,.wav,.m4a' },
];

export default function BottomSheet({ open, onClose }: BottomSheetProps) {
  const [selected, setSelected] = useState<InputType | null>(null);
  const [collection, setCollection] = useState('');
  const [textInput, setTextInput] = useState('');
  const [linkInput, setLinkInput] = useState('');
  const [fileName, setFileName] = useState('');
  const [fileSize, setFileSize] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const startIngestion = useIngestionStore((s) => s.startIngestion);
  const ingestionStatus = useIngestionStore((s) => s.status);
  const ingestionProgress = useIngestionStore((s) => s.progress);
  const entitiesFound = useIngestionStore((s) => s.entitiesFound);
  const relsFound = useIngestionStore((s) => s.relationshipsFound);
  const latestEntity = useIngestionStore((s) => s.latestEntity);
  const phase = useIngestionStore((s) => s.phase);

  if (!open) return null;

  const handleFileChange = () => {
    const file = fileRef.current?.files?.[0];
    if (file) {
      setFileName(file.name);
      const kb = file.size / 1024;
      setFileSize(kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${Math.round(kb)} KB`);
    }
  };

  const canSubmit = () => {
    if (selected === 'text') return !!textInput.trim();
    if (selected === 'link') return !!linkInput.trim();
    if (selected === 'file' || selected === 'folder' || selected === 'audio') return !!fileName;
    return false;
  };

  const handleSubmit = async () => {
    if (!canSubmit()) return;
    setSubmitting(true);
    setError('');
    const col = collection.trim() || 'Default';

    try {
      if (selected === 'text' && textInput.trim()) {
        const resp = await fetch('/api/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_type: 'text',
            source: textInput,
            options: { collection_name: col },
          }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        startIngestion(data.job_id);
      } else if (selected === 'link' && linkInput.trim()) {
        const isYT = linkInput.includes('youtube.com') || linkInput.includes('youtu.be');
        const resp = await fetch('/api/ingest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_type: isYT ? 'youtube' : 'url',
            source: linkInput,
            options: { collection_name: col },
          }),
        });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        startIngestion(data.job_id);
      } else if ((selected === 'file' || selected === 'folder' || selected === 'audio') && fileRef.current?.files?.[0]) {
        const file = fileRef.current.files[0];
        const formData = new FormData();
        formData.append('file', file);
        const st = selected === 'folder' ? 'folder' : selected === 'audio' ? 'audio' : 'pdf';
        formData.append('source_type', st);
        formData.append('collection_name', collection);
        const resp = await fetch('/api/ingest/file', { method: 'POST', body: formData });
        const data = await resp.json();
        if (data.error) throw new Error(data.error);
        startIngestion(data.job_id);
      }
      setSubmitted(true);
    } catch (err: any) {
      setError(err.message || 'Ingestion failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setSelected(null);
    setTextInput('');
    setLinkInput('');
    setFileName('');
    setFileSize('');
    setSubmitted(false);
    setError('');
    onClose();
  };

  const handleBack = () => {
    if (submitted) {
      setSubmitted(false);
      setSelected(null);
      setTextInput('');
      setLinkInput('');
      setFileName('');
      setFileSize('');
    } else {
      setSelected(null);
    }
  };

  return (
    <div className="fixed inset-0 z-40 flex items-end justify-center" style={{ background: 'rgba(0,0,0,0.08)' }} onClick={handleClose}>
      <div
        className="w-full max-w-xl glass-1 rounded-t-3xl px-8 py-7"
        onClick={(e) => e.stopPropagation()}
        style={{ maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 -8px 40px rgba(107,141,214,0.08)' }}
      >

        {/* ─── Step 1: Choose input type ─── */}
        {!selected && !submitted && (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold" style={{ fontFamily: "'Syne', sans-serif", color: 'rgba(30,36,60,0.92)' }}>
                Add knowledge
              </h2>
              <button onClick={handleClose} className="text-text-muted hover:text-text-primary text-xl transition-colors">×</button>
            </div>
            <p className="text-[13px] text-text-muted">Choose how you want to add to your knowledge graph.</p>
            <div className="space-y-2">
              {INPUT_OPTIONS.map((opt) => (
                <button
                  key={opt.type}
                  onClick={() => setSelected(opt.type)}
                  className="w-full flex items-center gap-4 px-5 py-4 rounded-2xl glass-3 hover:bg-white/70 transition-all text-left group"
                  style={{ border: '1px solid rgba(180,200,230,0.20)' }}
                >
                  <span className="text-xl">{opt.icon}</span>
                  <div>
                    <span className="text-[14px] font-medium text-text-primary block" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                      {opt.label}
                    </span>
                    <span className="text-[12px] text-text-muted">{opt.desc}</span>
                  </div>
                  <span className="ml-auto text-text-muted group-hover:text-text-secondary text-sm">→</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ─── Step 2: Input details ─── */}
        {selected && !submitted && (
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <button onClick={handleBack} className="text-text-muted hover:text-text-primary text-sm transition-colors">←</button>
              <div>
                <h2 className="text-lg font-bold" style={{ fontFamily: "'Syne', sans-serif", color: 'rgba(30,36,60,0.92)' }}>
                  {INPUT_OPTIONS.find((o) => o.type === selected)?.icon}{' '}
                  {INPUT_OPTIONS.find((o) => o.type === selected)?.label}
                </h2>
              </div>
              <button onClick={handleClose} className="ml-auto text-text-muted hover:text-text-primary text-xl transition-colors">×</button>
            </div>

            {/* Collection name */}
            <div className="space-y-1.5">
              <label className="text-[12px] font-medium text-text-secondary" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Collection name
              </label>
              <input
                type="text"
                value={collection}
                onChange={(e) => setCollection(e.target.value)}
                placeholder='e.g. "Research papers", "Meeting notes Q1"'
                className="w-full glass-2 rounded-xl px-4 py-3 text-[13px] text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-300/30 transition-shadow"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              />
            </div>

            {/* Type-specific input */}
            {selected === 'text' && (
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-text-secondary">Content</label>
                <textarea
                  value={textInput}
                  onChange={(e) => setTextInput(e.target.value)}
                  placeholder="Paste your text, notes, or article here..."
                  rows={6}
                  className="w-full glass-2 rounded-xl px-4 py-3 text-[13px] text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-300/30 resize-none transition-shadow"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                />
                {textInput && (
                  <p className="text-[11px] text-text-muted text-right">{textInput.length.toLocaleString()} characters</p>
                )}
              </div>
            )}

            {selected === 'link' && (
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-text-secondary">URL</label>
                <input
                  type="url"
                  value={linkInput}
                  onChange={(e) => setLinkInput(e.target.value)}
                  placeholder="https://... or YouTube URL"
                  className="w-full glass-2 rounded-xl px-4 py-3 text-[13px] text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-300/30 transition-shadow"
                  style={{ fontFamily: "'DM Sans', sans-serif" }}
                />
              </div>
            )}

            {(selected === 'file' || selected === 'folder' || selected === 'audio') && (
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-text-secondary">File</label>
                <input
                  ref={fileRef}
                  type="file"
                  accept={INPUT_OPTIONS.find((o) => o.type === selected)?.accept}
                  className="hidden"
                  id="bottom-sheet-file"
                  onChange={handleFileChange}
                />
                {!fileName ? (
                  <label
                    htmlFor="bottom-sheet-file"
                    className="flex flex-col items-center gap-2 glass-2 rounded-xl px-4 py-8 cursor-pointer hover:bg-white/70 transition-all"
                    style={{ border: '2px dashed rgba(107,141,214,0.25)' }}
                  >
                    <span className="text-2xl">📎</span>
                    <span className="text-[13px] text-text-secondary" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                      Click to choose a file
                    </span>
                    <span className="text-[11px] text-text-muted">
                      {INPUT_OPTIONS.find((o) => o.type === selected)?.accept}
                    </span>
                  </label>
                ) : (
                  <div
                    className="flex items-center gap-3 glass-2 rounded-xl px-4 py-4"
                    style={{ border: '1.5px solid rgba(107,141,214,0.20)' }}
                  >
                    <span className="text-xl">📄</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[13px] font-medium text-text-primary truncate" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                        {fileName}
                      </p>
                      <p className="text-[11px] text-text-muted">{fileSize}</p>
                    </div>
                    <button
                      onClick={() => { setFileName(''); setFileSize(''); if (fileRef.current) fileRef.current.value = ''; }}
                      className="text-text-muted hover:text-red-400 text-sm transition-colors"
                    >
                      ×
                    </button>
                  </div>
                )}
              </div>
            )}

            {error && (
              <div className="glass-3 rounded-xl px-4 py-3 text-[13px] text-red-500" style={{ border: '1px solid rgba(239,68,68,0.15)' }}>
                {error}
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={submitting || !canSubmit()}
              className="w-full py-4 rounded-xl text-[14px] font-semibold transition-all disabled:opacity-25 disabled:cursor-not-allowed"
              style={{
                fontFamily: "'Syne', sans-serif",
                background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
                color: '#fff',
                letterSpacing: '0.02em',
              }}
            >
              {submitting ? 'Starting extraction...' : 'Extract knowledge →'}
            </button>
          </div>
        )}

        {/* ─── Step 3: Confirmation + Progress ─── */}
        {submitted && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold" style={{ fontFamily: "'Syne', sans-serif", color: 'rgba(30,36,60,0.92)' }}>
                Extracting knowledge
              </h2>
              <button onClick={handleClose} className="text-text-muted hover:text-text-primary text-xl transition-colors">×</button>
            </div>

            {/* What was submitted */}
            <div className="glass-2 rounded-xl px-5 py-4 space-y-2" style={{ border: '1px solid rgba(107,141,214,0.12)' }}>
              <div className="flex items-center gap-2">
                <span className="text-sm">{INPUT_OPTIONS.find((o) => o.type === selected)?.icon}</span>
                <span className="text-[13px] font-medium text-text-primary">{collection || 'Untitled collection'}</span>
              </div>
              <p className="text-[12px] text-text-muted">
                {selected === 'text' && `${textInput.length.toLocaleString()} characters of text`}
                {selected === 'link' && linkInput}
                {(selected === 'file' || selected === 'folder' || selected === 'audio') && `${fileName} (${fileSize})`}
              </p>
            </div>

            {/* Progress bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[12px]">
                <span className="font-medium text-text-secondary" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  {ingestionStatus === 'complete' ? 'Done!' : phase || 'Starting...'}
                </span>
                <span className="text-text-muted">{Math.round(ingestionProgress)}%</span>
              </div>
              <div className="h-2 rounded-full glass-3 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${ingestionProgress}%`,
                    background: ingestionStatus === 'complete'
                      ? '#96e0b8'
                      : ingestionStatus === 'error'
                        ? '#ef4444'
                        : 'linear-gradient(90deg, #6b8dd6, #9b6bd6)',
                  }}
                />
              </div>
            </div>

            {/* Live stats */}
            <div className="grid grid-cols-2 gap-3">
              <div className="glass-3 rounded-xl px-4 py-3 text-center">
                <p className="text-xl font-bold text-text-primary" style={{ fontFamily: "'Syne', sans-serif" }}>
                  {entitiesFound}
                </p>
                <p className="text-[11px] text-text-muted">Entities found</p>
              </div>
              <div className="glass-3 rounded-xl px-4 py-3 text-center">
                <p className="text-xl font-bold text-text-primary" style={{ fontFamily: "'Syne', sans-serif" }}>
                  {relsFound}
                </p>
                <p className="text-[11px] text-text-muted">Relationships</p>
              </div>
            </div>

            {/* Latest entity */}
            {latestEntity && (
              <div className="glass-3 rounded-xl px-4 py-3">
                <p className="text-[11px] text-text-muted mb-1">Latest extraction</p>
                <p className="text-[13px] font-medium text-text-primary" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                  {latestEntity}
                </p>
              </div>
            )}

            {/* Actions */}
            {ingestionStatus === 'complete' ? (
              <div className="space-y-3">
                <div className="glass-2 rounded-xl px-5 py-4 text-center" style={{ border: '1px solid rgba(150,224,184,0.25)' }}>
                  <p className="text-[14px] font-medium text-text-primary">
                    Extracted {entitiesFound} entities and {relsFound} relationships
                  </p>
                  <p className="text-[12px] text-text-muted mt-1">Your knowledge graph has been updated.</p>
                </div>
                <div className="flex gap-3">
                  <button
                    onClick={handleBack}
                    className="flex-1 py-3 rounded-xl text-[13px] font-medium glass-3 text-text-secondary hover:text-text-primary transition-colors"
                  >
                    Add more
                  </button>
                  <button
                    onClick={handleClose}
                    className="flex-1 py-3 rounded-xl text-[13px] font-semibold transition-all"
                    style={{ background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)', color: '#fff' }}
                  >
                    View graph
                  </button>
                </div>
              </div>
            ) : ingestionStatus === 'error' ? (
              <div className="space-y-3">
                <div className="glass-3 rounded-xl px-4 py-3 text-[13px] text-red-500" style={{ border: '1px solid rgba(239,68,68,0.15)' }}>
                  Extraction failed. Try again or use a smaller input.
                </div>
                <button
                  onClick={handleBack}
                  className="w-full py-3 rounded-xl text-[13px] font-medium glass-3 text-text-secondary hover:text-text-primary transition-colors"
                >
                  ← Try again
                </button>
              </div>
            ) : (
              <p className="text-[12px] text-text-muted text-center">
                You can close this and the extraction will continue in the background.
              </p>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
