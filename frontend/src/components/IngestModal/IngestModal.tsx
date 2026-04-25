import { useState, useCallback, useRef, useEffect } from 'react';
import { useIngestionStore } from '../../stores/ingestionStore';
import { colorForType } from '../../stores/graphStore';

const API_BASE = '';

interface IngestModalProps {
  onClose: () => void;
}

export default function IngestModal({ onClose }: IngestModalProps) {
  const [inputText, setInputText] = useState('');
  const [inputMode, setInputMode] = useState<'text' | 'url' | 'youtube'>('text');
  const [collapsed, setCollapsed] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  const {
    isIngesting,
    progress,
    entitiesFound,
    relationshipsFound,
    status,
    phase,
    detail,
    latestEntity,
    latestType,
    chunk,
    totalChunks,
    error,
    entityLog,
    startIngestion,
    setError,
    reset,
  } = useIngestionStore();

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [entityLog.length]);

  useEffect(() => {
    if (status === 'extracting' || status === 'storing') {
      setCollapsed(true);
    }
  }, [status]);

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
  }, [inputMode, inputText, handleIngest]);

  const handleDone = () => {
    reset();
    onClose();
  };

  // Not ingesting yet — show full input form
  if (status === 'idle') {
    return (
      <div className="fixed bottom-0 left-0 right-0 z-40" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
        <div className="mx-auto max-w-[640px] rounded-t-2xl glass-1 overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-5 pt-4 pb-3">
            <h2
              className="text-[14px] font-semibold text-text-primary"
              style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.03em' }}
            >
              Ingest Knowledge
            </h2>
            <button
              onClick={onClose}
              className="h-7 w-7 rounded-lg flex items-center justify-center text-text-muted hover:text-text-primary transition-colors"
            >
              <svg className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="px-5 pb-4 space-y-3">
            {/* Mode tabs */}
            <div className="flex rounded-lg p-0.5 glass-3">
              {(['text', 'url', 'youtube'] as const).map((mode) => (
                <button
                  key={mode}
                  onClick={() => setInputMode(mode)}
                  className={`flex-1 rounded-md px-3 py-1.5 text-[11px] font-medium transition-all ${
                    inputMode === mode
                      ? 'bg-white/40 text-text-primary shadow-sm'
                      : 'text-text-secondary hover:text-text-primary'
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
                  ? 'Paste any text — articles, notes, research papers...'
                  : inputMode === 'url'
                    ? 'https://...'
                    : 'YouTube URL...'
              }
              className="w-full rounded-lg glass-3 px-4 py-3 text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none resize-none transition-all"
              rows={4}
            />

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={handleSubmit}
                disabled={!inputText.trim()}
                className={`flex-1 rounded-lg px-4 py-2.5 text-[12px] font-medium transition-all ${
                  !inputText.trim()
                    ? 'glass-3 text-text-muted cursor-not-allowed'
                    : 'text-white hover:shadow-md'
                }`}
                style={inputText.trim() ? {
                  background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
                } : {}}
              >
                Extract Knowledge
              </button>

              <label className="flex items-center justify-center rounded-lg glass-3 px-4 py-2.5 text-[12px] font-medium text-text-secondary hover:text-text-primary transition-all cursor-pointer">
                <svg className="h-3.5 w-3.5 mr-1.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v-8m-4 4l4-4 4 4M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                PDF
                <input type="file" accept=".pdf" onChange={handleFileUpload} className="hidden" />
              </label>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Ingesting or complete — progress bar
  return (
    <div className="fixed bottom-0 left-0 right-0 z-40">
      <div className="mx-auto max-w-[640px] rounded-t-2xl glass-1 overflow-hidden">
        {/* Header */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-between px-5 py-3 hover:bg-white/10 transition-colors"
        >
          <div className="flex items-center gap-3">
            {status === 'complete' ? (
              <span className="h-2.5 w-2.5 rounded-full" style={{ background: '#96e0b8' }} />
            ) : status === 'error' ? (
              <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
            ) : (
              <span className="h-2.5 w-2.5 rounded-full animate-pulse" style={{ background: '#6b8dd6' }} />
            )}

            <span className="text-[13px] font-medium text-text-primary">
              {status === 'complete'
                ? `Extracted ${entitiesFound} entities, ${relationshipsFound} relationships`
                : status === 'error'
                  ? 'Extraction failed'
                  : `Extracting... ${entitiesFound} entities found`}
            </span>

            {isIngesting && latestEntity && (
              <span
                className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  backgroundColor: colorForType(latestType) + '20',
                  color: colorForType(latestType),
                }}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />
                {latestEntity}
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {isIngesting && totalChunks > 0 && (
              <span className="text-[11px] text-text-muted tabular-nums" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
                Chunk {chunk}/{totalChunks}
              </span>
            )}
            <svg
              className={`h-4 w-4 text-text-muted transition-transform ${collapsed ? '' : 'rotate-180'}`}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </div>
        </button>

        {/* Progress bar */}
        <div className="h-1 w-full" style={{ background: 'rgba(180,200,230,0.15)' }}>
          <div
            className="h-full transition-all duration-300 ease-out"
            style={{
              width: `${Math.min(progress, 100)}%`,
              background:
                status === 'error'
                  ? '#ef4444'
                  : status === 'complete'
                    ? '#96e0b8'
                    : 'linear-gradient(90deg, #6b8dd6, #9b6bd6)',
            }}
          />
        </div>

        {/* Expanded details */}
        {!collapsed && (
          <div className="px-5 py-3 space-y-3">
            <div className="flex items-center gap-6 text-[12px]">
              <div className="flex items-center gap-1.5">
                <span className="text-text-muted">Entities</span>
                <span className="stat-number text-text-primary text-[16px]">{entitiesFound}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="text-text-muted">Relations</span>
                <span className="stat-number text-text-primary text-[16px]">{relationshipsFound}</span>
              </div>
              <div className="flex-1" />
              <span className="text-[11px] text-text-muted">{detail || phase}</span>
            </div>

            {entityLog.length > 0 && (
              <div ref={logRef} className="max-h-[120px] overflow-y-auto space-y-1 rounded-lg glass-3 p-2">
                {entityLog.map((entry, i) => (
                  <div key={i} className="flex items-center gap-2 text-[11px]">
                    <span
                      className="h-1.5 w-1.5 rounded-full shrink-0"
                      style={{ backgroundColor: colorForType(entry.type) }}
                    />
                    <span className="text-text-muted">{entry.type}</span>
                    <span className="text-text-primary">{entry.name}</span>
                  </div>
                ))}
              </div>
            )}

            {error && (
              <div className="text-[12px] text-red-500 bg-red-100/50 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            {(status === 'complete' || status === 'error') && (
              <button
                onClick={handleDone}
                className="w-full rounded-lg px-3 py-2 text-[12px] font-medium transition-colors"
                style={{
                  background: 'linear-gradient(135deg, rgba(107,141,214,0.15), rgba(155,107,214,0.10))',
                  border: '1px solid rgba(107,141,214,0.3)',
                  color: '#4a6ab8',
                }}
              >
                {status === 'complete' ? 'Done' : 'Close'}
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
