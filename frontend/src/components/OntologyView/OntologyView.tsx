import { useMemo } from 'react';
import { useGraphStore, colorForType } from '../../stores/graphStore';
import type { ReagraphNode, ReagraphEdge } from '../../stores/graphStore';

interface EntityTypeStat {
  type: string;
  count: number;
  color: string;
  examples: string[];
}

interface RelationshipTypeStat {
  label: string;
  count: number;
  exampleSource: string;
  exampleTarget: string;
}

export default function OntologyView() {
  const nodes = useGraphStore((s) => s.nodes);
  const edges = useGraphStore((s) => s.edges);

  const entityStats = useMemo<EntityTypeStat[]>(() => {
    const byType = new Map<string, ReagraphNode[]>();
    for (const node of nodes) {
      const type = String(node.data?.type || 'Unknown');
      const list = byType.get(type) || [];
      list.push(node);
      byType.set(type, list);
    }
    return Array.from(byType.entries())
      .map(([type, group]) => ({
        type,
        count: group.length,
        color: colorForType(type),
        examples: group.slice(0, 3).map((n) => n.label),
      }))
      .sort((a, b) => b.count - a.count);
  }, [nodes]);

  const relationshipStats = useMemo<RelationshipTypeStat[]>(() => {
    const byLabel = new Map<string, ReagraphEdge[]>();
    for (const edge of edges) {
      const label = edge.label || 'RELATED_TO';
      const list = byLabel.get(label) || [];
      list.push(edge);
      byLabel.set(label, list);
    }
    const nodeMap = new Map(nodes.map((n) => [n.id, n]));
    return Array.from(byLabel.entries())
      .map(([label, group]) => {
        const example = group[0];
        return {
          label,
          count: group.length,
          exampleSource: nodeMap.get(example.source)?.label || example.source,
          exampleTarget: nodeMap.get(example.target)?.label || example.target,
        };
      })
      .sort((a, b) => b.count - a.count);
  }, [edges, nodes]);

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center px-6">
        <p className="text-text-muted text-[13px] text-center leading-relaxed">
          No graph data yet. Ingest a document or add entities to see the ontology.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-5 pt-5 pb-3">
        <h2 className="text-[16px] font-semibold text-text-primary tracking-tight">
          Ontology
        </h2>
        <p className="text-[11px] text-text-muted mt-1">
          {entityStats.length} entity class{entityStats.length !== 1 ? 'es' : ''} &middot;{' '}
          {relationshipStats.length} relationship type{relationshipStats.length !== 1 ? 's' : ''}
        </p>
      </div>

      <div className="mx-5 border-t border-border" />

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto px-5 pb-5">
        {/* Entity Classes */}
        <div className="pt-4 pb-2">
          <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
            Entity Classes
          </span>
        </div>

        <div className="space-y-2">
          {entityStats.map((stat) => (
            <div key={stat.type} className="panel-inner p-3">
              <div className="flex items-center gap-2.5 mb-1.5">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ backgroundColor: stat.color }}
                />
                <span className="text-[13px] font-medium text-text-primary flex-1">
                  {stat.type}
                </span>
                <span className="stat-number text-[16px] text-accent">{stat.count}</span>
              </div>
              {stat.examples.length > 0 && (
                <div className="pl-5 text-[11px] text-text-muted leading-relaxed truncate">
                  {stat.examples.join(', ')}
                  {stat.count > 3 && ` +${stat.count - 3} more`}
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Relationship Types */}
        {relationshipStats.length > 0 && (
          <>
            <div className="pt-5 pb-2">
              <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-text-muted">
                Relationship Types
              </span>
            </div>

            <div className="space-y-2">
              {relationshipStats.map((stat) => (
                <div key={stat.label} className="panel-inner p-3">
                  <div className="flex items-center gap-2.5 mb-1.5">
                    <span className="text-[13px] font-medium text-text-primary flex-1 font-mono">
                      {stat.label}
                    </span>
                    <span className="stat-number text-[16px] text-accent">{stat.count}</span>
                  </div>
                  <div className="text-[11px] text-text-secondary leading-relaxed truncate">
                    <span className="text-text-muted">e.g.</span>{' '}
                    {stat.exampleSource}
                    <span className="text-text-muted mx-1">{'\u2192'}</span>
                    {stat.exampleTarget}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
