import { create } from 'zustand';

export type ActivityType = 'user' | 'agent' | 'tool_start' | 'tool_result' | 'thinking' | 'system';

export interface ActivityEntry {
  id: string;
  type: ActivityType;
  text: string;
  icon?: string;
  timestamp: number;
  toolName?: string;
  toolArgs?: string;
  status?: 'running' | 'done' | 'error';
}

interface VoiceState {
  isConnected: boolean;
  isRecording: boolean;
  isPanelOpen: boolean;

  // Full activity log (chat + tools + thinking)
  activity: ActivityEntry[];

  // Legacy transcript (for compatibility)
  transcript: { role: 'user' | 'agent'; text: string; timestamp: number }[];

  setConnected: (connected: boolean) => void;
  setRecording: (recording: boolean) => void;
  setPanelOpen: (open: boolean) => void;
  addTranscript: (role: 'user' | 'agent', text: string) => void;
  addActivity: (type: ActivityType, text: string, extra?: Partial<ActivityEntry>) => void;
  updateActivity: (id: string, updates: Partial<ActivityEntry>) => void;
  clearTranscript: () => void;
}

let _activityId = 0;

export const useVoiceStore = create<VoiceState>((set) => ({
  isConnected: false,
  isRecording: false,
  isPanelOpen: false,
  activity: [],
  transcript: [],

  setConnected: (connected) => set({ isConnected: connected }),
  setRecording: (recording) => set({ isRecording: recording }),
  setPanelOpen: (open) => set({ isPanelOpen: open }),

  addTranscript: (role, text) =>
    set((state) => ({
      transcript: [...state.transcript, { role, text, timestamp: Date.now() }],
      // Also add to activity log
      activity: [...state.activity, {
        id: `act-${++_activityId}`,
        type: role,
        text,
        timestamp: Date.now(),
      }],
      // Auto-open panel when agent responds
      isPanelOpen: role === 'agent' ? true : state.isPanelOpen,
    })),

  addActivity: (type, text, extra) =>
    set((state) => ({
      activity: [...state.activity, {
        id: `act-${++_activityId}`,
        type,
        text,
        timestamp: Date.now(),
        ...extra,
      }],
      isPanelOpen: true,
    })),

  updateActivity: (id, updates) =>
    set((state) => ({
      activity: state.activity.map((a) =>
        a.id === id ? { ...a, ...updates } : a
      ),
    })),

  clearTranscript: () => set({ transcript: [], activity: [] }),
}));
