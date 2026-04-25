import { useState } from 'react';

const ROLE_CHIPS = [
  'PhD student / researcher',
  'Medical professional',
  'Policy analyst',
  'Journalist / investigator',
  'Startup founder',
  'Engineer / developer',
  'Just exploring',
];

const DOMAIN_CHIPS = [
  'Life sciences / medicine',
  'Physical sciences',
  'Social sciences',
  'Law & policy',
  'Business & strategy',
  'Computer science',
  'Multiple / interdisciplinary',
];

interface OnboardingProps {
  onComplete: (role: string, domain: string) => void;
}

export default function Onboarding({ onComplete }: OnboardingProps) {
  const [step, setStep] = useState<'role' | 'domain'>('role');
  const [role, setRole] = useState('');
  const [domain, setDomain] = useState('');

  const handleFinish = () => {
    const profile = {
      role,
      domain,
      onboarded_at: new Date().toISOString(),
    };
    localStorage.setItem('voicegraph_onboarded', 'true');
    localStorage.setItem('voicegraph_profile', JSON.stringify(profile));

    fetch('/api/user/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(profile),
    }).catch(() => {});

    onComplete(role, domain);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center mesh-bg">
      <div className="w-full max-w-xl px-10 py-12 glass-1 rounded-3xl" style={{ boxShadow: '0 8px 60px rgba(107,141,214,0.10)' }}>

        {step === 'role' && (
          <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.15em]" style={{ fontFamily: "'Syne', sans-serif", color: '#6b8dd6' }}>
                Step 1 of 2
              </p>
              <h1 className="text-3xl font-bold" style={{ fontFamily: "'Syne', sans-serif", color: 'rgba(30,36,60,0.92)' }}>
                Who are you?
              </h1>
              <p className="text-[15px] text-text-muted leading-relaxed">
                This shapes how VoiceGraph builds and interprets your knowledge graph.
              </p>
            </div>

            {/* Text input */}
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. PhD researcher in computational biology, Cardiologist at NYU..."
              className="w-full glass-2 rounded-xl px-5 py-4 text-[14px] text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none focus:ring-2 focus:ring-indigo-300/40 transition-shadow"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            />

            {/* Chips */}
            <div className="flex flex-wrap gap-2.5">
              {ROLE_CHIPS.map((chip) => (
                <button
                  key={chip}
                  onClick={() => setRole(chip)}
                  className="transition-all"
                  style={{
                    padding: '10px 18px',
                    borderRadius: 12,
                    fontSize: 13,
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: role === chip ? 600 : 400,
                    background: role === chip ? 'linear-gradient(135deg, rgba(107,141,214,0.18), rgba(155,107,214,0.14))' : 'rgba(255,255,255,0.45)',
                    border: role === chip ? '1.5px solid rgba(107,141,214,0.35)' : '1px solid rgba(180,200,230,0.30)',
                    color: role === chip ? 'rgba(30,36,60,0.92)' : 'rgba(30,36,60,0.55)',
                    backdropFilter: 'blur(8px)',
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Continue */}
            <button
              onClick={() => role.trim() && setStep('domain')}
              disabled={!role.trim()}
              className="w-full py-4 rounded-xl text-[15px] font-semibold transition-all disabled:opacity-25 cursor-pointer disabled:cursor-not-allowed"
              style={{
                fontFamily: "'Syne', sans-serif",
                background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
                color: '#fff',
                letterSpacing: '0.02em',
              }}
            >
              Continue
            </button>
          </div>
        )}

        {step === 'domain' && (
          <div className="space-y-8">
            {/* Header */}
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-[0.15em]" style={{ fontFamily: "'Syne', sans-serif", color: '#9b6bd6' }}>
                Step 2 of 2
              </p>
              <h1 className="text-3xl font-bold" style={{ fontFamily: "'Syne', sans-serif", color: 'rgba(30,36,60,0.92)' }}>
                What's your domain?
              </h1>
              <p className="text-[15px] text-text-muted leading-relaxed">
                We'll tailor extraction and organization to your field.
              </p>
            </div>

            {/* Text input */}
            <input
              type="text"
              value={domain}
              onChange={(e) => setDomain(e.target.value)}
              placeholder="e.g. Kidney disease research, Constitutional law, Climate tech..."
              className="w-full glass-2 rounded-xl px-5 py-4 text-[14px] text-text-primary placeholder:text-text-muted bg-transparent focus:outline-none focus:ring-2 focus:ring-violet-300/40 transition-shadow"
              style={{ fontFamily: "'DM Sans', sans-serif" }}
            />

            {/* Chips */}
            <div className="flex flex-wrap gap-2.5">
              {DOMAIN_CHIPS.map((chip) => (
                <button
                  key={chip}
                  onClick={() => setDomain(chip)}
                  className="transition-all"
                  style={{
                    padding: '10px 18px',
                    borderRadius: 12,
                    fontSize: 13,
                    fontFamily: "'DM Sans', sans-serif",
                    fontWeight: domain === chip ? 600 : 400,
                    background: domain === chip ? 'linear-gradient(135deg, rgba(155,107,214,0.18), rgba(107,141,214,0.14))' : 'rgba(255,255,255,0.45)',
                    border: domain === chip ? '1.5px solid rgba(155,107,214,0.35)' : '1px solid rgba(180,200,230,0.30)',
                    color: domain === chip ? 'rgba(30,36,60,0.92)' : 'rgba(30,36,60,0.55)',
                    backdropFilter: 'blur(8px)',
                  }}
                >
                  {chip}
                </button>
              ))}
            </div>

            {/* Summary + actions */}
            {domain.trim() && (
              <p className="text-[14px] text-text-secondary text-center leading-relaxed" style={{ fontFamily: "'DM Sans', sans-serif" }}>
                Great — building your graph as a <span className="font-semibold text-text-primary">{role}</span> in <span className="font-semibold text-text-primary">{domain}</span>.
              </p>
            )}

            <div className="space-y-3">
              <button
                onClick={handleFinish}
                disabled={!domain.trim()}
                className="w-full py-4 rounded-xl text-[15px] font-semibold transition-all disabled:opacity-25 cursor-pointer disabled:cursor-not-allowed"
                style={{
                  fontFamily: "'Syne', sans-serif",
                  background: 'linear-gradient(135deg, #6b8dd6, #9b6bd6)',
                  color: '#fff',
                  letterSpacing: '0.02em',
                }}
              >
                Start building →
              </button>
              <button
                onClick={() => setStep('role')}
                className="w-full py-2.5 text-[13px] text-text-muted hover:text-text-primary transition-colors"
                style={{ fontFamily: "'DM Sans', sans-serif" }}
              >
                ← Back
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
