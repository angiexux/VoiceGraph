import { create } from 'zustand';

interface IngestionState {
  isIngesting: boolean;
  currentJobId: string | null;
  phase: string;
  detail: string;
  progress: number;
  entitiesFound: number;
  relationshipsFound: number;
  latestEntity: string;
  latestType: string;
  chunk: number;
  totalChunks: number;
  status: 'idle' | 'parsing' | 'extracting' | 'storing' | 'complete' | 'error';
  error: string | null;
  entityLog: { name: string; type: string; timestamp: number }[];

  startIngestion: (jobId: string) => void;
  updateProgress: (update: {
    phase?: string;
    detail?: string;
    progress?: number;
    entities?: number;
    relationships?: number;
    latestEntity?: string;
    latestType?: string;
    chunk?: number;
    totalChunks?: number;
    status?: string;
  }) => void;
  setComplete: (entities?: number, relationships?: number) => void;
  setError: (error: string) => void;
  reset: () => void;
}

export const useIngestionStore = create<IngestionState>((set) => ({
  isIngesting: false,
  currentJobId: null,
  phase: '',
  detail: '',
  progress: 0,
  entitiesFound: 0,
  relationshipsFound: 0,
  latestEntity: '',
  latestType: '',
  chunk: 0,
  totalChunks: 0,
  status: 'idle',
  error: null,
  entityLog: [],

  startIngestion: (jobId) =>
    set({
      isIngesting: true,
      currentJobId: jobId,
      phase: 'Parsing',
      detail: 'Preparing text...',
      progress: 0,
      entitiesFound: 0,
      relationshipsFound: 0,
      latestEntity: '',
      latestType: '',
      chunk: 0,
      totalChunks: 0,
      status: 'parsing',
      error: null,
      entityLog: [],
    }),

  updateProgress: (update) =>
    set((state) => {
      const newLog = [...state.entityLog];
      if (update.latestEntity && update.latestEntity !== state.latestEntity) {
        newLog.push({
          name: update.latestEntity,
          type: update.latestType || 'Entity',
          timestamp: Date.now(),
        });
        // Keep last 50
        if (newLog.length > 50) newLog.shift();
      }
      return {
        phase: update.phase || state.phase,
        detail: update.detail || state.detail,
        progress: update.progress ?? state.progress,
        entitiesFound: update.entities ?? state.entitiesFound,
        relationshipsFound: update.relationships ?? state.relationshipsFound,
        latestEntity: update.latestEntity || state.latestEntity,
        latestType: update.latestType || state.latestType,
        chunk: update.chunk ?? state.chunk,
        totalChunks: update.totalChunks ?? state.totalChunks,
        status: (update.status as IngestionState['status']) || state.status,
        entityLog: newLog,
      };
    }),

  setComplete: (entities, relationships) =>
    set((state) => ({
      isIngesting: false,
      status: 'complete',
      progress: 100,
      phase: 'Complete',
      detail: 'Extraction finished',
      entitiesFound: entities ?? state.entitiesFound,
      relationshipsFound: relationships ?? state.relationshipsFound,
    })),

  setError: (error) =>
    set({
      isIngesting: false,
      status: 'error',
      error,
    }),

  reset: () =>
    set({
      isIngesting: false,
      currentJobId: null,
      phase: '',
      detail: '',
      progress: 0,
      entitiesFound: 0,
      relationshipsFound: 0,
      latestEntity: '',
      latestType: '',
      chunk: 0,
      totalChunks: 0,
      status: 'idle',
      error: null,
      entityLog: [],
    }),
}));
