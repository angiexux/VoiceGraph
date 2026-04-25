import { useGraphStore, colorForType } from '../../stores/graphStore';
import IngestionPanel from '../Ingestion/IngestionPanel';

export default function LeftPanel() {
  const nodes = useGraphStore((s) => s.nodes);
  const edges = useGraphStore((s) => s.edges);

  const typeCounts: Record<string, number> = {};
  for (const node of nodes) {
    const t = (node.data?.type as string) || 'Unknown';
    typeCounts[t] = (typeCounts[t] || 0) + 1;
  }

  return (
    <div className="panel flex flex-col overflow-hidden max-h-[calc(100vh-5rem)]">
      {/* Header */}
      <div className="p-5 pb-4">
        <div className="flex items-center gap-2.5 mb-1">
          <div
            className="h-7 w-7 rounded-lg flex items-center justify-center"
            style={{
              background: 'linear-gradient(135deg, rgba(245,158,11,0.2), rgba(245,158,11,0.05))',
              border: '1px solid rgba(245,158,11,0.15)',
            }}
          >
            <svg className="h-3.5 w-3.5 text-accent" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18.5a6.5 6.5 0 100-13 6.5 6.5 0 000 13zM12 2v2m0 16v2M2 12h2m16 0h2" />
            </svg>
          </div>
          <div>
            <h1 className="text-[15px] font-semibold text-text-primary tracking-tight">
              VoiceGraph
            </h1>
          </div>
        </div>
      </div>

      <div className="mx-5 border-t border-border" />

      <div className="flex-1 overflow-y-auto p-5 pt-4 space-y-5">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="panel-inner p-3.5 text-center">
            <div className="stat-number text-[28px] text-accent">
              {nodes.length}
            </div>
            <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-text-muted mt-1.5">
              Nodes
            </div>
          </div>
          <div className="panel-inner p-3.5 text-center">
            <div className="stat-number text-[28px] text-secondary">
              {edges.length}
            </div>
            <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-text-muted mt-1.5">
              Edges
            </div>
          </div>
        </div>

        {/* Entity types */}
        {Object.keys(typeCounts).length > 0 && (
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.1em] text-text-muted mb-2.5">
              Entity Types
            </div>
            <div className="space-y-0.5">
              {Object.entries(typeCounts)
                .sort(([, a], [, b]) => b - a)
                .map(([type, count]) => (
                  <div
                    key={type}
                    className="flex items-center justify-between px-2.5 py-[7px] rounded-lg hover:bg-white/[0.03] transition-colors cursor-default"
                  >
                    <div className="flex items-center gap-2.5">
                      <span
                        className="h-[7px] w-[7px] rounded-full shrink-0"
                        style={{
                          backgroundColor: colorForType(type),
                          boxShadow: `0 0 6px ${colorForType(type)}50`,
                        }}
                      />
                      <span className="text-[13px] text-text-primary">{type}</span>
                    </div>
                    <span className="text-[12px] tabular-nums text-text-muted">
                      {count}
                    </span>
                  </div>
                ))}
            </div>
          </div>
        )}

        <div className="border-t border-border" />

        {/* Ingestion */}
        <IngestionPanel />
      </div>
    </div>
  );
}
