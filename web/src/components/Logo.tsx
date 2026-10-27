export function LogoMark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M32 6 54 14v17c0 13-9 22-22 27C19 53 10 44 10 31V14z" fill="#6c7bff" stroke="#1c1b3a" strokeWidth="4" strokeLinejoin="round" />
      <path d="m22 32 7 7 14-15" fill="none" stroke="#fffbf3" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="flex items-center gap-2.5">
      <LogoMark />
      <span className="font-display text-2xl font-extrabold tracking-tight">ASPARe</span>
    </span>
  );
}

/** Friendly shield character used in illustrations. */
export function Mascot({ size = 120, mood = "happy" }: { size?: number; mood?: "happy" | "wink" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 120 120" role="img" aria-label="ASPARe shield mascot">
      <path d="M60 8 104 24v32c0 25-17 42-44 52C33 98 16 81 16 56V24z" fill="#ffc83d" stroke="#1c1b3a" strokeWidth="4" strokeLinejoin="round" />
      <path d="M60 22 90 33v22c0 17-11 28-30 36C41 83 30 72 30 55V33z" fill="#fffbf3" stroke="#1c1b3a" strokeWidth="3" strokeLinejoin="round" />
      <circle cx="48" cy="52" r="5" fill="#1c1b3a" />
      {mood === "wink" ? (
        <path d="M66 52h12" stroke="#1c1b3a" strokeWidth="4" strokeLinecap="round" />
      ) : (
        <circle cx="72" cy="52" r="5" fill="#1c1b3a" />
      )}
      <path d="M48 68c4 8 20 8 24 0" fill="none" stroke="#1c1b3a" strokeWidth="4" strokeLinecap="round" />
      <circle cx="40" cy="64" r="4" fill="#ff8fb8" />
      <circle cx="80" cy="64" r="4" fill="#ff8fb8" />
    </svg>
  );
}
