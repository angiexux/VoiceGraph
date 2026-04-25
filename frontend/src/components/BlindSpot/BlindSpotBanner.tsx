import { useState, useEffect } from 'react';
import { useGraphStore } from '../../stores/graphStore';

export default function BlindSpotBanner() {
  const [data, setData] = useState<{ orphan_count: number; orphan_nodes: any[] } | null>(null);
  const [dismissed, setDismissed] = useState(false);
  const nodeCount = useGraphStore((s) => s.nodeCount);

  useEffect(() => {
    // Only check at 25-node milestones
    if (nodeCount > 0 && nodeCount % 25 === 0) {
      fetch('/api/user/blind-spots')
        .then((r) => r.json())
        .then((d) => {
          if (d.orphan_count > 0) {
            setData(d);
            setDismissed(false);
          }
        })
        .catch(() => {});
    }
  }, [nodeCount]);

  if (!data || dismissed || data.orphan_count === 0) return null;

  const handleExplore = () => {
    const ids = data.orphan_nodes.map((n: any) => n.id).filter(Boolean);
    if (ids.length > 0) {
      useGraphStore.getState().setHighlight(ids, []);
    }
  };

  return (
    <div className="glass-3 rounded-xl px-4 py-2.5 flex items-center justify-between text-xs">
      <span className="text-text-secondary">
        {data.orphan_count} concepts in your graph connect to nothing yet.
      </span>
      <div className="flex gap-2">
        <button
          onClick={handleExplore}
          className="text-text-primary hover:underline"
        >
          Explore them →
        </button>
        <button
          onClick={() => setDismissed(true)}
          className="text-text-muted hover:text-text-secondary"
        >
          ×
        </button>
      </div>
    </div>
  );
}
