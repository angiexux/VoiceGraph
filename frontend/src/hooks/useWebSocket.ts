import { useEffect, useRef, useCallback } from 'react';
import { useVoiceStore } from '../stores/voiceStore';
import { useGraphStore } from '../stores/graphStore';
import { useIngestionStore } from '../stores/ingestionStore';
import type { ClientEvent, ServerEvent } from '../types/events';

const WS_PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${WS_PROTOCOL}//${window.location.host}/ws/voice`;
const RECONNECT_BASE_MS = 1000;
const MAX_RECONNECT_ATTEMPTS = 10;

export function useWebSocket(onAudioChunk?: (base64Data: string) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onAudioChunkRef = useRef(onAudioChunk);
  onAudioChunkRef.current = onAudioChunk;

  const setConnected = useVoiceStore((s) => s.setConnected);
  const addTranscript = useVoiceStore((s) => s.addTranscript);
  const addActivity = useVoiceStore((s) => s.addActivity);

  const graphStore = useGraphStore;
  const ingestionStore = useIngestionStore;

  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const data: ServerEvent = JSON.parse(event.data);
        const state = graphStore.getState();

        switch (data.type) {
          // ---- Transcript ----
          case 'transcript':
            addTranscript(data.role, data.text);
            if (data.role === 'agent') {
              state.setLastAgentResponse(data.text);
            }
            break;

          // ---- Graph mutations ----
          case 'graph_update':
            state.setGraph(data.nodes, data.edges);
            break;

          case 'node_added':
            state.addNode(data.node);
            break;

          case 'edge_added':
            state.addEdge(data.edge);
            break;

          case 'node_removed':
            state.removeNode(data.nodeId);
            break;

          // ---- Thinking animations ----
          case 'thinking_start':
            state.thinkingStart(data.query);
            addActivity('thinking', data.query, { icon: '🧠' });
            break;

          case 'thinking_step':
            state.thinkingAddStep(data.step, data.icon, data.nodeId);
            addActivity('thinking', data.step, { icon: data.icon || '🔍' });
            break;

          case 'thinking_traverse':
            state.thinkingTraverse(data.fromId, data.toId, data.edgeId);
            break;

          case 'thinking_ripple':
            state.thinkingRipple(data.centerId, data.rings);
            break;

          case 'thinking_complete':
            state.thinkingComplete(data.resultNodeIds, data.resultEdgeIds);
            break;

          case 'thinking_clear':
            state.thinkingClear();
            break;

          // ---- Audio ----
          case 'audio_chunk':
            onAudioChunkRef.current?.(data.data);
            break;

          // ---- Status events ----
          case 'ingestion_status': {
            const ingState = ingestionStore.getState();
            if (data.status === 'complete') {
              ingState.setComplete(data.entities_found, data.relationships_found);
            } else if (data.status === 'error') {
              ingState.setError(data.error || 'Unknown error');
            } else {
              ingState.updateProgress({
                phase: data.phase || data.status,
                detail: data.detail || '',
                progress: typeof data.progress === 'number' ? data.progress * 100 : undefined,
                entities: data.entities_found,
                relationships: data.relationships_found,
                latestEntity: data.latest_entity,
                latestType: data.latest_type,
                chunk: data.chunk,
                totalChunks: data.total_chunks,
                status: data.status,
              });
            }
            break;
          }
          case 'ontology_changed':
          case 'csv_analysis':
            break;

          case 'error':
            console.error('[WS] Server error:', data.message);
            addActivity('system', `Error: ${data.message}`);
            break;

          default: {
            const untyped = data as Record<string, unknown>;
            if (untyped.type === 'highlight') {
              const rawNodeIds = (untyped.nodeIds as string[]) || [];
              const edgeIds = (untyped.edgeIds as string[]) || [];
              // Resolve: try matching by ID first, then by label/name (case-insensitive)
              const storeNodeList = state.nodes;
              const storeIdSet = new Set(storeNodeList.map((n) => n.id));
              const resolvedIds: string[] = [];
              for (const nid of rawNodeIds) {
                if (storeIdSet.has(nid)) {
                  resolvedIds.push(nid);
                } else {
                  // Try matching by label (entity name)
                  const lower = nid.toLowerCase();
                  const matched = storeNodeList.filter(
                    (n) => n.label.toLowerCase().includes(lower) || lower.includes(n.label.toLowerCase())
                  );
                  for (const m of matched) resolvedIds.push(m.id);
                }
              }
              console.log('[Highlight] raw:', rawNodeIds, 'resolved:', resolvedIds, 'storeNodes:', storeNodeList.length);
              state.setHighlight(resolvedIds, edgeIds);
            } else if (untyped.type === 'voice_ready') {
              addActivity('system', 'Voice session connected');
            } else if (untyped.type === 'voice_stopped') {
              addActivity('system', 'Voice session ended');
            } else if (untyped.type === 'voice_interrupted') {
              addActivity('system', 'Interrupted — listening...');
              // Clear any in-progress thinking state
              state.thinkingClear();
            } else if (untyped.type === 'tool_call_start') {
              // Store tool name so we can update it when result comes
              (window as any).__lastToolActivityId = `act-${(window as any).__nextActId || 0}`;
              addActivity('tool_start', `${untyped.tool_name}`, {
                toolName: untyped.tool_name as string,
                toolArgs: JSON.stringify(untyped.args || {}),
                status: 'running',
              });
            } else if (untyped.type === 'tool_call_result') {
              // Update the running tool_start entry to done
              const voiceState = useVoiceStore.getState();
              const runningTool = voiceState.activity.findLast(
                (a: any) => a.type === 'tool_start' && a.status === 'running'
              );
              if (runningTool) {
                voiceState.updateActivity(runningTool.id, { status: 'done' });
              }
              addActivity('tool_result', untyped.summary as string || 'Done');
            } else if (untyped.type === 'turn_complete') {
              // Voice turn complete — don't log
            } else {
              console.warn('[WS] Unknown event type:', untyped.type);
            }
          }
        }
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    },
    [addTranscript, addActivity, graphStore, ingestionStore],
  );

  const sendEvent = useCallback((event: ClientEvent) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(event));
      // Log user actions to activity
      if (event.type === 'text_input') {
        // transcript will be logged via addTranscript
      } else if (event.type === 'start_voice') {
        useVoiceStore.getState().addActivity('system', 'Starting voice session...');
      }
    } else {
      console.warn('[WS] Cannot send, not connected');
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setConnected(true);
      reconnectAttempts.current = 0;
    };

    ws.onmessage = handleMessage;

    ws.onclose = () => {
      setConnected(false);
      wsRef.current = null;

      if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
        const delay = RECONNECT_BASE_MS * Math.pow(2, reconnectAttempts.current);
        reconnectTimer.current = setTimeout(() => {
          reconnectAttempts.current++;
          connect();
        }, delay);
      }
    };

    ws.onerror = () => {};

    wsRef.current = ws;
  }, [handleMessage, setConnected]);

  const disconnect = useCallback(() => {
    if (reconnectTimer.current) {
      clearTimeout(reconnectTimer.current);
      reconnectTimer.current = null;
    }
    reconnectAttempts.current = MAX_RECONNECT_ATTEMPTS;
    wsRef.current?.close();
  }, []);

  useEffect(() => {
    connect();
    (window as unknown as Record<string, unknown>).sendEvent = sendEvent;
    return () => {
      disconnect();
      delete (window as unknown as Record<string, unknown>).sendEvent;
    };
  }, [connect, disconnect, sendEvent]);

  return { sendEvent, connect, disconnect };
}
