import { useEffect, useState } from 'react';
import { useGraphStore } from '../../stores/graphStore';

interface WikiPage {
  id: string;
  title: string;
  generated_at: string;
  entity_count: number;
  source_hint: string;
  job_id: string;
}

interface WikiPageDetail {
  title: string;
  content_md: string;
  questions: string[];
  generated_at: string;
  linked_entities: { id: string; name: string }[];
}

export function WikiView() {
  const [pages, setPages] = useState<WikiPage[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WikiPageDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const setHighlight = useGraphStore((s) => s.setHighlight);

  useEffect(() => {
    fetch('/api/wiki')
      .then((r) => r.json())
      .then((data) => setPages(data.pages || []))
      .catch(() => setPages([]));
  }, []);

  const loadPage = async (jobId: string) => {
    setSelectedJobId(jobId);
    setLoading(true);
    try {
      const res = await fetch(`/api/wiki/${jobId}`);
      const data = await res.json();
      setDetail(data);
      // Highlight linked nodes in the 3D graph
      const nodeIds = (data.linked_entities || []).map((e: { id: string }) => e.id);
      if (nodeIds.length > 0) setHighlight(nodeIds, []);
    } catch {
      setDetail(null);
    } finally {
      setLoading(false);
    }
  };

  // Very simple markdown → HTML converter (bold, italic, headers, lists, tables)
  const renderMd = (md: string) => {
    return md
      .replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold mt-4 mb-1 text-white/90">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-lg font-bold mt-6 mb-2 text-white">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold mb-4 text-white">$1</h1>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/^- (.+)$/gm, '<li class="ml-4 list-disc text-white/80">$1</li>')
      .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal text-white/80">$1</li>')
      .replace(/\n\n/g, '</p><p class="mb-3 text-white/75">')
      .replace(/^\|(.+)\|$/gm, (row) => {
        const cells = row.split('|').filter(Boolean).map((c) => c.trim());
        return '<tr>' + cells.map((c) => `<td class="border border-white/20 px-2 py-1 text-sm text-white/80">${c}</td>`).join('') + '</tr>';
      });
  };

  return (
    <div className="flex h-full bg-black/80 text-white">
      {/* Sidebar — page list */}
      <div className="w-72 border-r border-white/10 flex flex-col">
        <div className="p-4 border-b border-white/10">
          <h2 className="font-semibold text-white/90">Wiki Pages</h2>
          <p className="text-xs text-white/50 mt-0.5">{pages.length} pages generated</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {pages.length === 0 && (
            <p className="p-4 text-sm text-white/40">
              No wiki pages yet. Ingest a document to auto-generate one.
            </p>
          )}
          {pages.map((page) => (
            <button
              key={page.job_id}
              onClick={() => loadPage(page.job_id)}
              className={`w-full text-left p-4 border-b border-white/5 hover:bg-white/5 transition-colors ${
                selectedJobId === page.job_id ? 'bg-white/10' : ''
              }`}
            >
              <p className="text-sm font-medium text-white/90 line-clamp-2">{page.title}</p>
              <p className="text-xs text-white/40 mt-1">{page.entity_count} entities</p>
              <p className="text-xs text-white/30">{new Date(page.generated_at).toLocaleDateString('en-US')}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Main panel — page content */}
      <div className="flex-1 overflow-y-auto">
        {!detail && !loading && (
          <div className="flex items-center justify-center h-full text-white/30 text-sm">
            Select a wiki page to read it
          </div>
        )}
        {loading && (
          <div className="flex items-center justify-center h-full text-white/50 text-sm">
            Loading...
          </div>
        )}
        {detail && !loading && (
          <div className="max-w-3xl mx-auto p-8">
            {/* Questions to Explore chips */}
            {detail.questions.length > 0 && (
              <div className="mb-6 p-4 bg-white/5 rounded-lg border border-white/10">
                <p className="text-xs text-white/50 uppercase tracking-wide mb-3">Questions to Explore</p>
                <div className="flex flex-wrap gap-2">
                  {detail.questions.map((q, i) => (
                    <span
                      key={i}
                      className="text-xs bg-blue-500/20 text-blue-300 border border-blue-500/30 px-3 py-1.5 rounded-full cursor-default"
                    >
                      {q}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Markdown content */}
            <div
              className="prose prose-invert max-w-none"
              dangerouslySetInnerHTML={{ __html: `<p class="mb-3 text-white/75">${renderMd(detail.content_md)}</p>` }}
            />

            {/* Linked entities */}
            {detail.linked_entities.length > 0 && (
              <div className="mt-8 pt-6 border-t border-white/10">
                <p className="text-xs text-white/50 uppercase tracking-wide mb-3">Graph Nodes</p>
                <div className="flex flex-wrap gap-2">
                  {detail.linked_entities.map((e) => (
                    <span
                      key={e.id}
                      className="text-xs bg-white/10 text-white/70 px-2 py-1 rounded border border-white/20"
                    >
                      {e.name}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
