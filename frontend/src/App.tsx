import { useState, useEffect, useCallback, useRef } from 'react';
import GraphView from './components/Graph/GraphView';
import QueryView from './components/QueryView/QueryView';
import OntologyView from './components/OntologyView/OntologyView';
import InfoSidebar from './components/InfoSidebar/InfoSidebar';
import TopBar from './components/TopBar/TopBar';
import BottomSheet from './components/BottomSheet/BottomSheet';
import Onboarding from './components/Onboarding/Onboarding';
import YourMind from './components/YourMind/YourMind';
import TimeSlider from './components/TimeSlider/TimeSlider';
import BlindSpotBanner from './components/BlindSpot/BlindSpotBanner';
import VoicePanel from './components/VoicePanel/VoicePanel';
import ThoughtStream from './components/ThoughtStream/ThoughtStream';
import ActivityPanel from './components/ActivityPanel/ActivityPanel';
import { useWebSocket } from './hooks/useWebSocket';
import { useAudioPlayback } from './hooks/useAudioPlayback';
import { useGraphStore } from './stores/graphStore';


export type View = 'graph' | 'query' | 'ontology' | 'mind';

/** Parse raw API graph response into store-compatible format */
function parseGraphResponse(data: any) {
  const nodes = (data.nodes || []).map((n: any) => ({
    id: n.id,
    label: n.properties?.name || n.label || n.id,
    type: n.labels?.[0] || n.properties?.entity_type || n.type || 'Entity',
    properties: n.properties || {},
  }));
  const edges = (data.edges || []).map((e: any) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.type || e.label || '',
    properties: e.properties || {},
  }));
  return { nodes, edges };
}

/** Fetch top-50 summary (default) or full graph. */
async function fetchAndLoadGraph(full = false): Promise<{ nodeCount: number; totalNodes: number }> {
  const url = full ? '/api/graph' : '/api/graph/summary';
  const resp = await fetch(url);
  const data = await resp.json();
  if (!data.nodes?.length) return { nodeCount: 0, totalNodes: data.total_nodes || 0 };

  const { nodes, edges } = parseGraphResponse(data);
  useGraphStore.getState().setGraph(nodes, edges);
  return { nodeCount: nodes.length, totalNodes: data.total_nodes || nodes.length };
}

function App() {
  const { playChunk, stopPlayback } = useAudioPlayback();
  const { sendEvent } = useWebSocket(playChunk);
  const selectedNodeId = useGraphStore((s) => s.selectedNodeId);
  const isThinking = useGraphStore((s) => s.isThinking);

  const [onboarded, setOnboarded] = useState(() =>
    localStorage.getItem('voicegraph_onboarded') === 'true'
  );

  const [currentView, setCurrentView] = useState<View>('graph');
  const [showIngest, setShowIngest] = useState(false);
  const [chatText, setChatText] = useState('');
  const [showingFull, setShowingFull] = useState(false);
  const [totalNodes, setTotalNodes] = useState(0);

  const handleChatSubmit = useCallback(() => {
    const trimmed = chatText.trim();
    if (!trimmed || isThinking) return;
    sendEvent({ type: 'text_input', text: trimmed });
    setChatText('');
  }, [chatText, isThinking, sendEvent]);

  const interruptCooldownRef = useRef(false);
  const handleInterrupt = useCallback(() => {
    if (interruptCooldownRef.current) return;
    interruptCooldownRef.current = true;
    setTimeout(() => { interruptCooldownRef.current = false; }, 2000);
    stopPlayback();
    sendEvent({ type: 'interrupt_voice' });
    useGraphStore.getState().thinkingClear();
  }, [stopPlayback, sendEvent]);

  useEffect(() => {
    if (onboarded) {
      fetchAndLoadGraph(false).then(({ totalNodes: t }) => setTotalNodes(t)).catch(() => {});
    }
  }, [onboarded]);

  const handleToggleFullGraph = useCallback(() => {
    const next = !showingFull;
    setShowingFull(next);
    fetchAndLoadGraph(next).then(({ totalNodes: t }) => setTotalNodes(t)).catch(() => {});
  }, [showingFull]);

  const handleOnboardingComplete = useCallback((_role: string, _domain: string) => {
    setOnboarded(true);
  }, []);

  if (!onboarded) {
    return <Onboarding onComplete={handleOnboardingComplete} />;
  }

  const hasRight = currentView === 'graph' && !!selectedNodeId;

  return (
    <div
      className="relative h-screen w-screen overflow-hidden"
      style={{
        display: 'grid',
        gridTemplateRows: '52px 1fr 56px',
        gridTemplateColumns: hasRight ? '260px 1fr 300px' : '260px 1fr',
        gridTemplateAreas: hasRight
          ? `"nav nav nav" "left main right" "bar bar bar"`
          : `"nav nav" "left main" "bar bar"`,
        gap: '8px',
        padding: '10px',
        zIndex: 1,
      }}
    >
      {/* ─── Nav ─── */}
      <div style={{ gridArea: 'nav' }}>
        <TopBar
          currentView={currentView}
          onViewChange={setCurrentView as (v: string) => void}
          onIngest={() => setShowIngest(true)}
        />
      </div>

      {/* ─── Left panel ─── */}
      <div style={{ gridArea: 'left', overflow: 'hidden' }} className="flex flex-col gap-2">
        <ActivityPanel />
        <YourMind />
      </div>

      {/* ─── Main content ─── */}
      <div style={{ gridArea: 'main', position: 'relative', overflow: 'hidden', borderRadius: '16px' }}>
        {currentView === 'graph' && (
          <GraphView
            showingFull={showingFull}
            totalNodes={totalNodes}
            onToggleFull={handleToggleFullGraph}
          />
        )}
        {currentView === 'query' && <QueryView sendEvent={sendEvent} />}
        {currentView === 'ontology' && <OntologyView />}

        <div className="absolute top-4 right-4 z-10">
          <ThoughtStream />
        </div>

        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10 w-[500px] max-w-[80%]">
          <BlindSpotBanner />
        </div>

        {currentView === 'graph' && (
          <div className="absolute bottom-16 left-1/2 -translate-x-1/2 z-10 w-[400px] max-w-[60%]">
            <TimeSlider />
          </div>
        )}
      </div>

      {/* ─── Right panel ─── */}
      {hasRight && (
        <div style={{ gridArea: 'right', overflow: 'hidden' }}>
          <InfoSidebar />
        </div>
      )}

      {/* ─── Bottom bar ─── */}
      <div
        style={{ gridArea: 'bar' }}
        className="glass-1 flex items-center gap-3 px-4 rounded-xl"
      >
        {/* Add source button */}
        <button
          onClick={() => setShowIngest(true)}
          className="shrink-0 h-9 w-9 rounded-xl flex items-center justify-center glass-3 hover:bg-white/60 transition-all"
          style={{
            fontSize: 18,
            color: 'rgba(30,36,60,0.50)',
            border: '1px solid rgba(180,200,230,0.25)',
          }}
          title="Add source"
        >
          +
        </button>

        {/* Text input */}
        <div className="flex-1 flex items-center gap-2 glass-2 rounded-xl px-4" style={{ height: 40 }}>
          <input
            type="text"
            value={chatText}
            onChange={(e) => setChatText(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleChatSubmit(); }}
            placeholder="Ask anything about your knowledge graph..."
            disabled={isThinking}
            className="flex-1 bg-transparent text-[13px] text-text-primary placeholder:text-text-muted focus:outline-none disabled:opacity-40"
            style={{ fontFamily: "'DM Sans', sans-serif" }}
          />

          {/* Ask */}
          <button
            onClick={handleChatSubmit}
            disabled={isThinking || !chatText.trim()}
            className="shrink-0 rounded-lg px-4 py-1.5 text-[12px] font-semibold disabled:opacity-25 disabled:cursor-not-allowed transition-all"
            style={{
              fontFamily: "'Syne', sans-serif",
              background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
              color: '#fff',
              letterSpacing: '0.02em',
            }}
          >
            Ask
          </button>
        </div>

        {/* Voice controls */}
        <div className="shrink-0 flex items-center gap-2">
          <VoicePanel sendEvent={sendEvent} />

          {/* Interrupt */}
          <button
            onClick={handleInterrupt}
            className="h-8 w-8 rounded-lg flex items-center justify-center transition-all hover:bg-red-50"
            style={{
              border: '1px solid rgba(239, 68, 68, 0.20)',
              color: '#ef4444',
            }}
            title="Interrupt agent"
          >
            <svg className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Status dot */}
        <div className="shrink-0 glass-3 flex items-center gap-2 px-3 py-1.5 rounded-lg">
          <span
            className="h-2 w-2 rounded-full"
            style={{
              background: isThinking ? '#96b8f0' : '#96e0b8',
              boxShadow: isThinking ? '0 0 6px rgba(150,184,240,0.6)' : '0 0 6px rgba(150,224,184,0.6)',
              animation: isThinking ? 'blink 0.8s ease-in-out infinite' : 'none',
            }}
          />
          <span
            className="text-[11px] font-medium text-text-secondary"
            style={{ fontFamily: "'DM Sans', sans-serif", letterSpacing: '0.02em' }}
          >
            {isThinking ? 'Thinking...' : 'Ready'}
          </span>
        </div>
      </div>

      {/* Bottom sheet */}
      <BottomSheet open={showIngest} onClose={() => setShowIngest(false)} />
    </div>
  );
}

export default App;
