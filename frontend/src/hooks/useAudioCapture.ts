import { useCallback, useRef, useEffect } from 'react';
import { useVoiceStore } from '../stores/voiceStore';
import type { ClientEvent } from '../types/events';

const SAMPLE_RATE = 16000;
const BUFFER_SIZE = 4096;

interface UseAudioCaptureOptions {
  sendEvent: (event: ClientEvent) => void;
}

export function useAudioCapture({ sendEvent }: UseAudioCaptureOptions) {
  const setRecording = useVoiceStore((s) => s.setRecording);

  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<ScriptProcessorNode | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const isRecordingRef = useRef(false);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      });
      streamRef.current = stream;

      const audioCtx = new AudioContext({ sampleRate: SAMPLE_RATE });
      audioCtxRef.current = audioCtx;

      const source = audioCtx.createMediaStreamSource(stream);

      // Create analyser for waveform visualization
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;

      // Use ScriptProcessorNode to capture raw PCM
      // (AudioWorklet would be better but requires a separate file)
      const processor = audioCtx.createScriptProcessor(BUFFER_SIZE, 1, 1);
      workletNodeRef.current = processor;

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current) return;

        const float32 = e.inputBuffer.getChannelData(0);

        // Convert float32 [-1,1] to int16 PCM
        const int16 = new Int16Array(float32.length);
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]));
          int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
        }

        // Convert to base64
        const bytes = new Uint8Array(int16.buffer);
        let binary = '';
        for (let i = 0; i < bytes.length; i++) {
          binary += String.fromCharCode(bytes[i]);
        }
        const base64 = btoa(binary);

        sendEvent({ type: 'audio_chunk', data: base64 });
      };

      source.connect(processor);
      processor.connect(audioCtx.destination);

      isRecordingRef.current = true;
      setRecording(true);
    } catch (err) {
      const error = err as Error;
      if (error.name === 'NotAllowedError') {
        console.error('[AudioCapture] Microphone permission denied');
      } else if (error.name === 'NotFoundError') {
        console.error('[AudioCapture] No microphone found');
      } else {
        console.error('[AudioCapture] Failed to start recording:', error);
      }
      throw err;
    }
  }, [sendEvent, setRecording]);

  const stopRecording = useCallback(() => {
    isRecordingRef.current = false;
    setRecording(false);

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current.onaudioprocess = null;
      workletNodeRef.current = null;
    }

    if (audioCtxRef.current) {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }

    analyserRef.current = null;
  }, [setRecording]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (isRecordingRef.current) {
        isRecordingRef.current = false;
        workletNodeRef.current?.disconnect();
        audioCtxRef.current?.close();
        streamRef.current?.getTracks().forEach((t) => t.stop());
      }
    };
  }, []);

  return {
    startRecording,
    stopRecording,
    analyserRef,
  };
}
