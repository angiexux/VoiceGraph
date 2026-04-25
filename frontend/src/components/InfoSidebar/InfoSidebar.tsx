import { useGraphStore, colorForType } from '../../stores/graphStore';

export default function InfoSidebar() {
  const nodes = useGraphStore((s) => s.nodes);
  const edges = useGraphStore((s) => s.edges);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const selectedNode = useGraphStore((s) => s.selectedNode);
  const selectNode = useGraphStore((s) => s.selectNode);

  const connectedEdges = selectedNodeId
    ? edges.filter((e) => e.source === selectedNodeId || e.target === selectedNodeId)
    : [];

  if (!selectedNode) return null;

  const typeColor = colorForType(selectedNode.data?.type as string | undefined);
  const typeName = String(selectedNode.data?.type || 'Entity');

  return (
    <div className="glass-1 h-full flex flex-col overflow-hidden p-3.5">
      {/* Header */}
      <div className="flex items-center justify-between pb-2 mb-2" style={{ borderBottom: '1px solid rgba(180,200,230,0.25)' }}>
        <span
          className="text-[11px] font-semibold uppercase text-text-muted"
          style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '0.08em' }}
        >
          Node Detail
        </span>
        <button
          onClick={() => selectNode(null)}
          className="h-6 w-6 rounded-md flex items-center justify-center text-text-muted hover:text-text-primary transition-colors"
        >
          <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Entity name */}
      <h2
        className="text-[20px] font-semibold text-text-primary leading-tight mb-1.5"
        style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '-0.03em' }}
      >
        {selectedNode.label}
      </h2>

      {/* Type badge */}
      <div
        className="glass-3 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md w-fit mb-3"
        style={{ background: `${typeColor}22` }}
      >
        <span
          className="h-[7px] w-[7px] rounded-full"
          style={{ backgroundColor: typeColor, border: '1.5px solid rgba(110,120,140,0.45)' }}
        />
        <span className="text-[10.5px] font-medium text-text-primary" style={{ letterSpacing: '0.02em' }}>
          {typeName}
        </span>
      </div>

      {/* Properties as description */}
      {selectedNode.data && Object.keys(selectedNode.data).filter(k => k !== 'type').length > 0 && (
        <div className="mb-3">
          {Object.entries(selectedNode.data)
            .filter(([key]) => key !== 'type')
            .slice(0, 3)
            .map(([key, val]) => (
              <div key={key} className="mb-2">
                <div className="text-[10px] font-medium uppercase text-text-muted mb-0.5" style={{ letterSpacing: '0.04em' }}>
                  {key}
                </div>
                <div className="text-[12px] text-text-primary leading-relaxed">
                  {String(val).length > 200 ? String(val).slice(0, 200) + '...' : String(val)}
                </div>
              </div>
            ))}
        </div>
      )}

      {/* Connections section */}
      <div className="flex items-center justify-between pb-2 mb-2" style={{ borderBottom: '1px solid rgba(180,200,230,0.25)' }}>
        <span
          className="text-[11px] font-semibold uppercase text-text-muted"
          style={{ fontFamily: "'Syne', sans-serif", letterSpacing: '0.08em' }}
        >
          Connections
        </span>
        <span className="text-[10px] text-text-muted" style={{ fontFamily: "'JetBrains Mono', monospace" }}>
          {connectedEdges.length}
        </span>
      </div>

      {/* Connections list */}
      <div className="flex-1 overflow-y-auto space-y-1.5">
        {connectedEdges.length > 0 ? (
          connectedEdges.map((edge) => {
            const isSource = edge.source === selectedNodeId;
            const otherNodeId = isSource ? edge.target : edge.source;
            const otherNode = nodes.find((n) => n.id === otherNodeId);
            const otherType = otherNode?.data?.type as string | undefined;
            const otherColor = colorForType(otherType);
            return (
              <button
                key={edge.id}
                onClick={() => selectNode(otherNodeId)}
                className="glass-3 flex w-full items-center gap-2 p-2 rounded-lg text-left transition-all hover:bg-white/30"
              >
                <span
                  className="h-[9px] w-[9px] rounded-full shrink-0"
                  style={{ backgroundColor: otherColor, border: '1.5px solid rgba(110,120,140,0.45)' }}
                />
                <span className="text-[12px] text-text-primary flex-1 truncate">
                  {otherNode?.label ?? otherNodeId}
                </span>
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: 'rgba(80,100,140,0.40)',
                    background: 'rgba(200,215,240,0.3)',
                  }}
                >
                  {edge.label}
                </span>
              </button>
            );
          })
        ) : (
          <div className="text-[12px] text-text-muted py-4">No connections found</div>
        )}
      </div>
    </div>
  );
}
