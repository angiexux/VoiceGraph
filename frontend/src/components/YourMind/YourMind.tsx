import { useState, useEffect } from 'react';

interface MindSummary {
  worldview: number;
  depth: number;
  top_clusters: { name: string; size: number; top_concepts: string[] }[];
  total_nodes: number;
  total_edges: number;
  orphan_count: number;
  coverage_percent: number;
  below_threshold?: boolean;
  message?: string;
}

export default function YourMind() {
  const [data, setData] = useState<MindSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/user/mind-summary')
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="glass-1 rounded-2xl p-5 text-center text-text-muted text-sm">
        Loading...
      </div>
    );
  }

  if (!data || data.below_threshold) {
    return (
      <div className="glass-1 rounded-2xl p-5 text-center">
        <p className="text-sm text-text-muted">
          {data?.message || 'Add more sources to unlock your knowledge profile.'}
        </p>
        <p className="text-xs text-text-muted mt-1">
          {data?.total_nodes || 0} / 50 concepts needed
        </p>
      </div>
    );
  }

  return (
    <div className="glass-1 rounded-2xl p-5 space-y-4">
      <h3 className="text-sm font-semibold text-text-primary">Your knowledge, mapped</h3>

      <div className="flex gap-4">
        <div className="text-center">
          <div className="text-2xl font-bold text-text-primary">{data.worldview}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Worldview</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-text-primary">{data.depth}</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Depth</div>
        </div>
        <div className="text-center">
          <div className="text-2xl font-bold text-text-primary">{data.coverage_percent}%</div>
          <div className="text-[10px] text-text-muted uppercase tracking-wider">Coverage</div>
        </div>
      </div>

      {data.top_clusters.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-xs text-text-muted">Top clusters:</div>
          {data.top_clusters.map((c, i) => (
            <div key={i} className="flex items-center gap-2 text-xs">
              <span className="h-2 w-2 rounded-full" style={{
                background: `hsla(${120 + i * 60}, 35%, 74%, 0.80)`,
              }} />
              <span className="text-text-primary">{c.name}</span>
              <span className="text-text-muted">({c.size} nodes)</span>
            </div>
          ))}
        </div>
      )}

      {data.orphan_count > 0 && (
        <button className="text-xs text-text-muted hover:text-text-secondary transition-colors">
          {data.orphan_count} orphan concepts →
        </button>
      )}
    </div>
  );
}
