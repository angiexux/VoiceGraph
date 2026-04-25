import { useState, useCallback } from 'react';
import { useIngestionStore } from '../../stores/ingestionStore';

const API_BASE = '';

export default function IngestionPanel() {
  const [inputText, setInputText] = useState('');
  const [inputMode, setInputMode] = useState<'text' | 'url' | 'youtube'>('text');

  const {
    isIngesting,
    progress,
    entitiesFound,
    relationshipsFound,
    status,
    error,
    startIngestion,
    setError,
    reset,
  } = useIngestionStore();

  const handleIngest = useCallback(
    async (sourceType: string, content: string) => {
      if (!content.trim()) return;
      const jobId = crypto.randomUUID();
      startIngestion(jobId);
      try {
        const response = await fetch(`${API_BASE}/api/ingest`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ source_type: sourceType, source: content.trim() }),
        });
        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Request failed' }));
          setError(errData.detail || `HTTP ${response.status}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error');
      }
    },
    [startIngestion, setError],
  );

  const handleFileUpload = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;
      const jobId = crypto.randomUUID();
      startIngestion(jobId);
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('job_id', jobId);
        const response = await fetch(`${API_BASE}/api/ingest/file`, {
          method: 'POST',
          body: formData,
        });
        if (!response.ok) {
          const errData = await response.json().catch(() => ({ detail: 'Upload failed' }));
          setError(errData.detail || `HTTP ${response.status}`);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Network error');
      }
      e.target.value = '';
    },
    [startIngestion, setError],
  );

  const handleSubmit = useCallback(() => {
    handleIngest(inputMode, inputText);
    setInputText('');
  }, [inputMode, inputText, handleIngest]);

  return (
    <div className="space-y-3">
      <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-text-muted">
        Ingest Data
      </div>

      {/* Mode tabs */}
      <div className="flex rounded-xl p-1 panel-inner">
        {(['text', 'url', 'youtube'] as const).map((mode) => (
          <button
            key={mode}
            onClick={() => setInputMode(mode)}
            className={`flex-1 rounded-lg px-2 py-[6px] text-[11px] font-medium transition-all ${
              inputMode === mode
                ? 'bg-white/[0.07] text-text-primary shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            {mode === 'youtube' ? 'YouTube' : mode.charAt(0).toUpperCase() + mode.slice(1)}
          </button>
        ))}
      </div>

      {/* Input */}
      <textarea
        value={inputText}
        onChange={(e) => setInputText(e.target.value)}
        placeholder={
          inputMode === 'text'
            ? 'Paste text to extract knowledge from...'
            : inputMode === 'url'
              ? 'https://...'
              : 'YouTube URL...'
        }
        disabled={isIngesting}
        className="w-full rounded-xl border border-border bg-white/[0.02] px-3.5 py-3 text-[13px] text-text-primary placeholder-text-muted/50 focus:border-accent/30 focus:outline-none focus:ring-1 focus:ring-accent/15 disabled:opacity-40 resize-none transition-all"
        rows={3}
      />

      {/* Actions */}
      <div className="flex gap-2">
        <button
          onClick={handleSubmit}
          disabled={isIngesting || !inputText.trim()}
          className={`flex-1 rounded-xl px-3 py-2.5 text-[11px] font-semibold uppercase tracking-[0.05em] transition-all ${
            isIngesting || !inputText.trim()
              ? 'bg-white/[0.04] text-text-muted cursor-not-allowed'
              : 'bg-accent text-bg-primary hover:shadow-[0_0_20px_rgba(245,158,11,0.3)] hover:-translate-y-px active:translate-y-0'
          }`}
        >
          {isIngesting ? 'Processing...' : 'Extract'}
        </button>

        <label
          className={`flex items-center justify-center rounded-xl border border-border px-3.5 py-2.5 text-[11px] font-medium text-text-muted hover:text-text-secondary hover:bg-white/[0.03] transition-all cursor-pointer ${
            isIngesting ? 'opacity-30 pointer-events-none' : ''
          }`}
        >
          PDF
          <input type="file" accept=".pdf" onChange={handleFileUpload} className="hidden" disabled={isIngesting} />
        </label>
      </div>

      {/* Progress */}
      {status !== 'idle' && (
        <div className="panel-inner p-3.5 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-text-secondary">
              {status === 'complete' ? 'Extraction complete' : status === 'error' ? 'Failed' : 'Extracting...'}
            </span>
            <span
              className={`inline-flex items-center gap-1.5 rounded-full px-2 py-[2px] text-[9px] font-semibold uppercase tracking-wider ${
                status === 'complete'
                  ? 'bg-secondary/15 text-secondary'
                  : status === 'error'
                    ? 'bg-error/15 text-error'
                    : 'bg-accent/15 text-accent'
              }`}
            >
              {!['idle', 'complete', 'error'].includes(status) && (
                <span className="h-1.5 w-1.5 rounded-full bg-accent animate-pulse" />
              )}
              {status}
            </span>
          </div>

          <div className="h-1 w-full rounded-full bg-white/[0.04] overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-700 ease-out"
              style={{
                width: `${Math.min(progress, 100)}%`,
                background: status === 'error' ? '#ef4444' : '#f59e0b',
              }}
            />
          </div>

          {(entitiesFound > 0 || relationshipsFound > 0) && (
            <div className="flex gap-4 text-[11px]">
              <span className="text-text-muted">
                Entities <span className="text-text-primary font-semibold ml-1">{entitiesFound}</span>
              </span>
              <span className="text-text-muted">
                Relations <span className="text-text-primary font-semibold ml-1">{relationshipsFound}</span>
              </span>
            </div>
          )}

          {error && <div className="text-[11px] text-error">{error}</div>}

          {(status === 'complete' || status === 'error') && (
            <button
              onClick={reset}
              className="w-full rounded-lg border border-border px-2 py-1.5 text-[10px] font-medium text-text-muted hover:text-text-primary hover:bg-white/[0.03] transition-colors"
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}
