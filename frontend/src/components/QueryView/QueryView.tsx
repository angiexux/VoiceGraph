import { useState, useCallback, useRef, useEffect } from 'react';
import { useGraphStore } from '../../stores/graphStore';

interface QueryViewProps {
  sendEvent: (event: any) => void;
}

interface QueryHistoryEntry {
  id: string;
  query: string;
  answer: string | null;
  entities: { id: string; label: string; type?: string }[];
  timestamp: number;
  status: 'pending' | 'complete' | 'error';
}

export default function QueryView({ sendEvent }: QueryViewProps) {
  const [queryText, setQueryText] = useState('');
  const [history, setHistory] = useState<QueryHistoryEntry[]>([]);
  const [activeEntryId, setActiveEntryId] = useState<string | null>(null);
  const resultAreaRef = useRef<HTMLDivElement>(null);

  const { isThinking, thinkingSteps, thinkingQuery, selectNode, nodes, lastAgentResponse } = useGraphStore();

  // Auto-scroll results area when new thinking steps arrive
  useEffect(() => {
    if (resultAreaRef.current) {
      resultAreaRef.current.scrollTop = resultAreaRef.current.scrollHeight;
    }
  }, [thinkingSteps]);

  const handleSubmit = useCallback(() => {
    const trimmed = queryText.trim();
    if (!trimmed || isThinking) return;

    const entryId = crypto.randomUUID();
    const entry: QueryHistoryEntry = {
      id: entryId,
      query: trimmed,
      answer: null,
      entities: [],
      timestamp: Date.now(),
      status: 'pending',
    };

    setHistory((prev) => [entry, ...prev]);
    setActiveEntryId(entryId);
    setQueryText('');

    sendEvent({ type: 'text_input', text: trimmed });
  }, [queryText, isThinking, sendEvent]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  // When thinking completes and agent responds, update the active history entry
  useEffect(() => {
    if (!isThinking && activeEntryId && lastAgentResponse) {
      const mentionedNodeIds = thinkingSteps
        .filter((s) => s.nodeId)
        .map((s) => s.nodeId!);
      const uniqueNodeIds = [...new Set(mentionedNodeIds)];
      const matchedEntities = uniqueNodeIds
        .map((nid) => {
          const node = nodes.find((n) => n.id === nid);
          return node
            ? { id: node.id, label: node.label, type: (node.data?.type as string) ?? undefined }
            : null;
        })
        .filter(Boolean) as { id: string; label: string; type?: string }[];

      setHistory((prev) =>
        prev.map((entry) =>
          entry.id === activeEntryId
            ? {
                ...entry,
                answer: lastAgentResponse,
                entities: matchedEntities,
                status: 'complete',
              }
            : entry,
        ),
      );
      setActiveEntryId(null);
    }
  }, [isThinking, activeEntryId, lastAgentResponse, thinkingSteps, nodes]);

  const activeEntry = history.find((e) => e.id === activeEntryId);
  const pastEntries = history.filter((e) => e.id !== activeEntryId);

  return (
    <div className="flex h-full gap-4 p-4">
      {/* ── Main query area ── */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Input area */}
        <div className="panel p-5 mb-4">
          <label className="block text-[12px] font-semibold uppercase tracking-[0.06em] text-text-muted mb-3">
            Ask the Knowledge Graph
          </label>
          <textarea
            value={queryText}
            onChange={(e) => setQueryText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="e.g. What connections exist between Einstein and quantum mechanics?"
            disabled={isThinking}
            rows={3}
            className="w-full rounded-xl border border-border bg-white/[0.02] px-4 py-3.5 text-[13px] text-text-primary placeholder-text-muted/50 focus:border-accent/30 focus:outline-none focus:ring-1 focus:ring-accent/15 disabled:opacity-40 resize-none transition-all"
          />
          <div className="flex items-center justify-between mt-3">
            <span className="text-[11px] text-text-muted">
              {isThinking ? 'Processing query...' : 'Press Enter to submit'}
            </span>
            <button
              onClick={handleSubmit}
              disabled={isThinking || !queryText.trim()}
              className={`rounded-xl px-6 py-2.5 text-[12px] font-semibold uppercase tracking-[0.04em] transition-all ${
                isThinking || !queryText.trim()
                  ? 'bg-white/[0.04] text-text-muted cursor-not-allowed'
                  : 'bg-accent text-bg-primary hover:shadow-[0_0_24px_rgba(245,158,11,0.35)] hover:-translate-y-px'
              }`}
            >
              {isThinking ? (
                <span className="flex items-center gap-2">
                  <svg className="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
                  </svg>
                  Querying...
                </span>
              ) : (
                'Query'
              )}
            </button>
          </div>
        </div>

        {/* Results area */}
        <div className="flex-1 min-h-0 overflow-y-auto" ref={resultAreaRef}>
          {/* Active query — live thinking */}
          {isThinking && (
            <div className="panel p-5 mb-4" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
              <div className="flex items-center gap-2 mb-4">
                <span className="h-2 w-2 rounded-full bg-accent animate-pulse" />
                <span className="text-[13px] font-medium text-text-primary">
                  {thinkingQuery || activeEntry?.query}
                </span>
              </div>

              {/* Thinking steps */}
              <div className="space-y-2">
                {thinkingSteps.map((step, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2.5 panel-inner px-3 py-2.5"
                    style={{ animation: 'fadeSlideIn 0.15s ease-out' }}
                  >
                    <span className="text-[14px] mt-px shrink-0">{step.icon || '\u2022'}</span>
                    <span className="text-[12px] text-text-secondary leading-relaxed">{step.step}</span>
                    {step.nodeId && (
                      <button
                        onClick={() => selectNode(step.nodeId!)}
                        className="ml-auto shrink-0 text-[10px] text-accent hover:text-accent-hover transition-colors"
                      >
                        view
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completed active entry (just finished) */}
          {!isThinking && activeEntry?.status === 'complete' && (
            <div className="panel p-5 mb-4" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
              <div className="flex items-center gap-2 mb-3">
                <svg className="h-4 w-4 text-secondary" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-[13px] font-medium text-text-primary">{activeEntry.query}</span>
              </div>
              <ResultBlock entry={activeEntry} onNodeClick={selectNode} />
            </div>
          )}

          {/* No results state */}
          {!isThinking && history.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <svg className="h-10 w-10 text-text-muted/30 mb-4" fill="none" stroke="currentColor" strokeWidth={1.5} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
              </svg>
              <p className="text-[13px] text-text-muted">Ask a question to explore the knowledge graph</p>
              <p className="text-[11px] text-text-muted/60 mt-1">The agent will search, traverse, and reason over your data</p>
            </div>
          )}
        </div>
      </div>

      {/* ── History sidebar ── */}
      {pastEntries.length > 0 && (
        <div className="w-64 shrink-0 flex flex-col min-h-0">
          <div className="panel flex-1 min-h-0 flex flex-col">
            <div className="p-4 pb-3">
              <h3 className="text-[12px] font-semibold uppercase tracking-[0.06em] text-text-muted">
                History
              </h3>
            </div>
            <div className="mx-4 border-t border-border" />
            <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
              {pastEntries.map((entry) => (
                <button
                  key={entry.id}
                  onClick={() => {
                    // Re-run the query
                    setQueryText(entry.query);
                  }}
                  className="w-full text-left rounded-lg px-3 py-2.5 hover:bg-white/[0.04] transition-colors group"
                >
                  <p className="text-[12px] text-text-secondary truncate group-hover:text-text-primary transition-colors">
                    {entry.query}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-1.5 py-[1px] text-[9px] font-semibold uppercase tracking-wider ${
                        entry.status === 'complete'
                          ? 'bg-secondary/15 text-secondary'
                          : entry.status === 'error'
                            ? 'bg-error/15 text-error'
                            : 'bg-accent/15 text-accent'
                      }`}
                    >
                      {entry.status}
                    </span>
                    {entry.entities.length > 0 && (
                      <span className="text-[10px] text-text-muted">
                        {entry.entities.length} entities
                      </span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Result block sub-component ── */

function ResultBlock({
  entry,
  onNodeClick,
}: {
  entry: QueryHistoryEntry;
  onNodeClick: (id: string) => void;
}) {
  return (
    <div className="space-y-4">
      {/* Answer */}
      {entry.answer && (
        <div className="panel-inner p-4">
          <p className="text-[12px] text-text-secondary leading-relaxed">{entry.answer}</p>
        </div>
      )}

      {/* Entities */}
      {entry.entities.length > 0 && (
        <div>
          <span className="text-[11px] font-medium uppercase tracking-[0.06em] text-text-muted mb-2 block">
            Relevant Entities
          </span>
          <div className="flex flex-wrap gap-1.5">
            {entry.entities.map((entity) => (
              <button
                key={entity.id}
                onClick={() => onNodeClick(entity.id)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-[11px] text-text-secondary hover:text-text-primary hover:border-accent/30 hover:bg-accent/5 transition-all"
              >
                <span
                  className="h-1.5 w-1.5 rounded-full shrink-0"
                  style={{ background: entityColor(entity.type) }}
                />
                {entity.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Helpers ── */

const TYPE_COLORS: Record<string, string> = {
  Person: '#60a5fa',
  Organization: '#a78bfa',
  Concept: '#34d399',
  Event: '#fbbf24',
  Location: '#fb7185',
  Technology: '#2dd4bf',
};

function entityColor(type?: string): string {
  return (type && TYPE_COLORS[type]) || '#8b5cf6';
}
