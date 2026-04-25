import { useEffect, useRef } from 'react';
import { useGraphStore } from '../../stores/graphStore';

export default function ThoughtStream() {
  const isThinking = useGraphStore((s) => s.isThinking);
  const thinkingQuery = useGraphStore((s) => s.thinkingQuery);
  const thinkingSteps = useGraphStore((s) => s.thinkingSteps);
  const thinkingClear = useGraphStore((s) => s.thinkingClear);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thinkingSteps.length]);

  if (!isThinking && thinkingSteps.length === 0) return null;

  return (
    <div
      className="glass-1 flex flex-col overflow-hidden"
      style={{ width: '300px', maxHeight: '280px' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-3.5 pb-2.5">
        <div className="flex items-center gap-2">
          {isThinking && (
            <span
              className="h-[6px] w-[6px] rounded-full"
              style={{
                background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
                boxShadow: '0 0 8px rgba(107,141,214,0.5)',
                animation: 'glow-pulse 1s ease-in-out infinite',
              }}
            />
          )}
          <span
            className="text-[11px] font-semibold uppercase"
            style={{
              fontFamily: "'Syne', sans-serif",
              letterSpacing: '0.08em',
              color: isThinking ? '#6b8dd6' : 'rgba(80,100,140,0.40)',
            }}
          >
            {isThinking ? 'Reasoning' : 'Done'}
          </span>
        </div>
        {!isThinking && (
          <button
            onClick={thinkingClear}
            className="text-text-muted hover:text-text-primary transition-colors p-1 rounded-md"
          >
            <svg className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="mx-4" style={{ borderTop: '1px solid rgba(180,200,230,0.25)' }} />

      {thinkingQuery && (
        <div className="px-4 py-2.5">
          <p
            className="italic text-[13px] text-text-secondary line-clamp-2"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          >
            &ldquo;{thinkingQuery}&rdquo;
          </p>
        </div>
      )}

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-2 space-y-1">
        {thinkingSteps.map((step, i) => (
          <div
            key={i}
            className="flex items-start gap-2 py-1"
            style={{
              animation: 'fadeSlideIn 0.25s ease-out',
              opacity: isThinking && i === thinkingSteps.length - 1 ? 1 : 0.55,
            }}
          >
            <span className="text-[13px] shrink-0 mt-px">{step.icon}</span>
            <span className="text-[12px] text-text-secondary leading-relaxed">
              {step.step}
            </span>
          </div>
        ))}

        {isThinking && (
          <div className="flex items-center gap-1.5 py-1 pl-6">
            {[0, 0.15, 0.3].map((delay) => (
              <span
                key={delay}
                className="h-1 w-1 rounded-full"
                style={{
                  background: '#6b8dd6',
                  animation: `glow-pulse 1s ease-in-out ${delay}s infinite`,
                }}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
