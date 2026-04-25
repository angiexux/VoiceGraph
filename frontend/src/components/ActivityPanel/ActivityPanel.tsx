import { useEffect, useRef } from 'react';
import { useVoiceStore, type ActivityEntry } from '../../stores/voiceStore';

export default function ActivityPanel() {
  const activity = useVoiceStore((s) => s.activity);
  const clearTranscript = useVoiceStore((s) => s.clearTranscript);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [activity]);

  return (
    <div className="glass-1 h-full flex flex-col overflow-hidden p-3.5">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 mb-2" style={{ borderBottom: '1px solid rgba(180,200,230,0.25)' }}>
        <span
          className="text-[11px] font-semibold uppercase text-text-muted"
          style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '0.08em' }}
        >
          Agent Trace
        </span>
        <button
          onClick={clearTranscript}
          className="rounded-md px-2 py-0.5 text-[10px] text-text-muted hover:text-text-secondary transition-colors"
        >
          Clear
        </button>
      </div>

      {/* Activity stream */}
      <div className="flex-1 overflow-y-auto space-y-2 pr-1" ref={scrollRef}>
        {activity.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <span className="text-[12px] text-text-muted">No activity yet</span>
            <span className="text-[11px] text-text-muted/60 mt-1">Speak or type to start</span>
          </div>
        )}

        {activity.map((entry) => (
          <ActivityRow key={entry.id} entry={entry} />
        ))}
      </div>
    </div>
  );
}

function ActivityRow({ entry }: { entry: ActivityEntry }) {
  switch (entry.type) {
    case 'user':
      return (
        <div className="flex flex-col gap-1" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
          <div className="glass-3 rounded-[10px] px-3 py-2 text-[12px] leading-relaxed text-text-primary">
            {entry.text}
          </div>
          <span className="text-[9.5px] text-text-muted pl-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {new Date(entry.timestamp).toLocaleTimeString('en', { hour12: false })} · you
          </span>
        </div>
      );

    case 'agent':
      return (
        <div className="flex flex-col gap-1" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
          <div className="glass-3 rounded-[10px] px-3 py-2 text-[12px] leading-relaxed text-text-primary">
            {entry.text}
          </div>
          <span className="text-[9.5px] text-text-muted pl-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {new Date(entry.timestamp).toLocaleTimeString('en', { hour12: false })} · agent
          </span>
        </div>
      );

    case 'tool_start':
      return (
        <div className="flex flex-col gap-1" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
          <div className="tool-pill">
            {entry.status === 'running' ? (
              <svg className="h-3 w-3 text-[#5070b0] animate-spin" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            ) : (
              <span className="text-[10px]">✓</span>
            )}
            <span>{entry.toolName || 'tool'}</span>
            {entry.status === 'running' && (
              <span className="text-[9px] opacity-60">running...</span>
            )}
          </div>
        </div>
      );

    case 'tool_result':
      return (
        <div className="flex flex-col gap-1 pl-2" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
          <div className="glass-3 rounded-[10px] px-3 py-2 text-[11px] leading-relaxed text-text-secondary">
            {entry.text}
          </div>
        </div>
      );

    case 'thinking':
      return (
        <div className="flex flex-col gap-1" style={{ animation: 'fadeSlideIn 0.2s ease-out' }}>
          <div
            className="glass-3 rounded-[10px] px-3 py-2 text-[12px] leading-relaxed text-text-primary"
            style={{
              borderLeft: '2px solid rgba(150,180,240,0.6)',
              animation: 'thinking-pulse 2s ease-in-out infinite',
            }}
          >
            <span className="mr-1.5">{entry.icon || '💭'}</span>
            {entry.text}
          </div>
          <span className="text-[9.5px] text-text-muted pl-1" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
            {new Date(entry.timestamp).toLocaleTimeString('en', { hour12: false })} · thinking
          </span>
        </div>
      );

    case 'system':
      return (
        <div className="flex items-center gap-2 py-1.5 px-1">
          <div className="flex-1 h-px" style={{ background: 'rgba(180,200,230,0.25)' }} />
          <span className="text-[10px] text-text-muted shrink-0">{entry.text}</span>
          <div className="flex-1 h-px" style={{ background: 'rgba(180,200,230,0.25)' }} />
        </div>
      );

    default:
      return null;
  }
}
