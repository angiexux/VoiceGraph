import { useGraphStore, colorForType } from '../../stores/graphStore';
import type { View } from '../../App';

interface TopBarProps {
  currentView: View;
  onViewChange: (view: View) => void;
  onIngest: () => void;
}

export default function TopBar(props: TopBarProps) {
  const { onIngest } = props;
  // currentView and onViewChange available via props if needed later
  const nodes = useGraphStore((s) => s.nodes);
  const edges = useGraphStore((s) => s.edges);

  // Entity type counts for filter pills
  const typeCounts: Record<string, number> = {};
  for (const node of nodes) {
    const t = (node.data?.type as string) || 'Unknown';
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  }

  const activeFilters = useGraphStore((s) => s.typeFilters);
  const toggleTypeFilter = useGraphStore((s) => s.toggleTypeFilter);

  return (
    <nav className="glass-1 flex items-center justify-between px-4 h-full gap-3">
      {/* Left: Logo */}
      <div className="flex items-center gap-2 shrink-0">
        <div
          className="w-2 h-2 rounded-full"
          style={{
            background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
            boxShadow: '0 0 8px rgba(107,141,214,0.5)',
            animation: 'pulse-dot 2.4s ease-in-out infinite',
          }}
        />
        <span
          className="text-[15px] font-bold text-text-primary whitespace-nowrap"
          style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.03em' }}
        >
          VoiceGraph
        </span>
      </div>

      {/* Center: Filter pills */}
      <div
        className="flex gap-1.5 flex-1 justify-center overflow-x-auto"
        style={{ scrollbarWidth: 'none' }}
      >
        <button
          onClick={() => toggleTypeFilter('__all__')}
          className={`whitespace-nowrap text-[11px] font-medium px-3 py-1 rounded-[20px] transition-all ${
            activeFilters.size === 0
              ? 'text-text-primary shadow-sm'
              : 'text-text-secondary hover:text-text-primary'
          }`}
          style={{
            letterSpacing: '0.02em',
            background: activeFilters.size === 0 ? 'rgba(107,141,214,0.15)' : 'rgba(255,255,255,0.20)',
            border: activeFilters.size === 0
              ? '1px solid rgba(255,255,255,0.70)'
              : '1px solid rgba(180,200,230,0.35)',
          }}
        >
          All
        </button>
        {Object.entries(typeCounts)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 8)
          .map(([type]) => {
            const color = colorForType(type);
            const isActive = activeFilters.has(type);
            return (
              <button
                key={type}
                onClick={() => toggleTypeFilter(type)}
                className={`flex items-center gap-1.5 whitespace-nowrap text-[11px] font-medium px-3 py-1 rounded-[20px] transition-all ${
                  isActive
                    ? 'text-text-primary shadow-sm'
                    : 'text-text-secondary hover:text-text-primary'
                }`}
                style={{
                  letterSpacing: '0.02em',
                  background: isActive ? `${color}22` : 'rgba(255,255,255,0.20)',
                  border: isActive
                    ? '1px solid rgba(255,255,255,0.70)'
                    : '1px solid rgba(180,200,230,0.35)',
                }}
              >
                <span
                  className="h-[6px] w-[6px] rounded-full"
                  style={{ backgroundColor: color }}
                />
                {type}
              </button>
            );
          })}
      </div>

      {/* Right: stats + ingest */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="glass-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md">
          <span className="text-[10px] text-text-secondary" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Nodes</span>
          <span className="text-[10px] font-medium text-text-primary" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{nodes.length}</span>
        </div>
        <div className="glass-3 flex items-center gap-1.5 px-2.5 py-1 rounded-md">
          <span className="text-[10px] text-text-secondary" style={{ fontFamily: "'JetBrains Mono', monospace" }}>Edges</span>
          <span className="text-[10px] font-medium text-text-primary" style={{ fontFamily: "'JetBrains Mono', monospace" }}>{edges.length}</span>
        </div>
        <button
          onClick={onIngest}
          className="text-[12px] font-medium px-4 py-1.5 rounded-[10px] transition-all hover:shadow-md"
          style={{
            background: 'linear-gradient(135deg, rgba(107,141,214,0.22), rgba(155,107,214,0.18))',
            border: '1px solid rgba(107,141,214,0.4)',
            color: '#4a6ab8',
            letterSpacing: '0.01em',
          }}
        >
          + Ingest
        </button>
      </div>
    </nav>
  );
}
