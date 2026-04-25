import { useState, useRef, useEffect } from 'react';
import { useGraphStore } from '../../stores/graphStore';

export default function TimeSlider() {
  const nodes = useGraphStore((s) => s.nodes);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [currentDate, setCurrentDate] = useState<number | null>(null);
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Compute date range from nodes
  const dates = nodes
    .map((n) => {
      const d = (n.data as any)?.document_created_at;
      return d ? new Date(d).getTime() : null;
    })
    .filter((d): d is number => d !== null)
    .sort((a, b) => a - b);

  const minDate = dates[0] || Date.now() - 365 * 24 * 3600 * 1000;
  const maxDate = dates[dates.length - 1] || Date.now();

  // If no dates, don't render
  if (dates.length < 2) return null;

  const handleSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = Number(e.target.value);
    setCurrentDate(val);
    // Material mutation will happen via parent watching this
  };

  const togglePlay = () => {
    if (playing) {
      if (animRef.current) clearInterval(animRef.current);
      animRef.current = null;
      setPlaying(false);
    } else {
      const start = currentDate || minDate;
      let t = start;
      const step = ((maxDate - minDate) / 200) * speed;
      setPlaying(true);
      animRef.current = setInterval(() => {
        t += step;
        if (t >= maxDate) {
          t = maxDate;
          setCurrentDate(t);
          if (animRef.current) clearInterval(animRef.current);
          setPlaying(false);
          return;
        }
        setCurrentDate(t);
      }, 50);
    }
  };

  useEffect(() => {
    return () => {
      if (animRef.current) clearInterval(animRef.current);
    };
  }, []);

  const fmtDate = (ts: number) => new Date(ts).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });

  return (
    <div className="glass-3 rounded-xl px-4 py-2 flex items-center gap-3">
      <button
        onClick={togglePlay}
        className="text-text-secondary hover:text-text-primary text-sm transition-colors shrink-0"
      >
        {playing ? '⏸' : '▶'}
      </button>
      <div className="flex-1 flex flex-col gap-0.5">
        <input
          type="range"
          min={minDate}
          max={maxDate}
          value={currentDate || maxDate}
          onChange={handleSlider}
          className="w-full h-1 rounded-full appearance-none cursor-pointer"
          style={{ accentColor: 'hsla(45, 80%, 65%, 0.85)' }}
        />
        <div className="flex justify-between text-[9px] text-text-muted">
          <span>{fmtDate(minDate)}</span>
          <span>{currentDate ? fmtDate(currentDate) : 'Now'}</span>
          <span>{fmtDate(maxDate)}</span>
        </div>
      </div>
      <div className="flex gap-1 shrink-0">
        {[1, 5, 10].map((s) => (
          <button
            key={s}
            onClick={() => setSpeed(s)}
            className={`text-[9px] px-1.5 py-0.5 rounded ${
              speed === s ? 'text-text-primary glass-2' : 'text-text-muted'
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
}
