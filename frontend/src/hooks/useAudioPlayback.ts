import { useCallback, useRef, useState } from 'react';

const OUTPUT_SAMPLE_RATE = 24000;

export function useAudioPlayback() {
  const audioCtxRef = useRef<AudioContext | null>(null);
  const nextStartTimeRef = useRef(0);
  const activeSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const [isPlaying, setIsPlaying] = useState(false);

  const getAudioContext = useCallback(() => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });
      nextStartTimeRef.current = 0;
    }
    // Resume if suspended (browser autoplay policy)
    if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  }, []);

  const playChunk = useCallback(
    (base64Data: string) => {
      const ctx = getAudioContext();

      // Decode base64 to raw bytes
      const binary = atob(base64Data);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
      }

      // Interpret as 16-bit PCM signed
      const int16 = new Int16Array(bytes.buffer);
      const numSamples = int16.length;

      if (numSamples === 0) return;

      // Convert int16 PCM to float32 for Web Audio
      const float32 = new Float32Array(numSamples);
      for (let i = 0; i < numSamples; i++) {
        float32[i] = int16[i] / 0x8000;
      }

      // Create audio buffer
      const audioBuffer = ctx.createBuffer(1, numSamples, OUTPUT_SAMPLE_RATE);
      audioBuffer.copyToChannel(float32, 0);

      // Schedule playback to chain seamlessly after previous chunk
      const source = ctx.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(ctx.destination);

      const now = ctx.currentTime;
      const startTime = Math.max(now, nextStartTimeRef.current);

      source.start(startTime);
      nextStartTimeRef.current = startTime + audioBuffer.duration;

      activeSourcesRef.current.add(source);
      setIsPlaying(true);

      source.onended = () => {
        activeSourcesRef.current.delete(source);
        if (activeSourcesRef.current.size === 0) {
          setIsPlaying(false);
        }
      };
    },
    [getAudioContext],
  );

  const stopPlayback = useCallback(() => {
    activeSourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {
        // Already stopped
      }
    });
    activeSourcesRef.current.clear();
    nextStartTimeRef.current = 0;
    setIsPlaying(false);

    if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
  }, []);

  return { playChunk, stopPlayback, isPlaying };
}
