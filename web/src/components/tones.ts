export type Tone = "peri" | "coral" | "sun" | "mint" | "lilac" | "sky" | "pink";

export const TONE: Record<Tone, { solid: string; soft: string; text: string }> = {
  peri: { solid: "bg-peri text-white", soft: "bg-peri-100", text: "text-peri" },
  coral: { solid: "bg-coral text-white", soft: "bg-coral-100", text: "text-coral" },
  sun: { solid: "bg-sun text-ink", soft: "bg-sun-100", text: "text-warn" },
  mint: { solid: "bg-mint text-ink", soft: "bg-mint-100", text: "text-ok" },
  lilac: { solid: "bg-lilac text-ink", soft: "bg-lilac-100", text: "text-lilac" },
  sky: { solid: "bg-sky text-ink", soft: "bg-sky-100", text: "text-sky" },
  pink: { solid: "bg-pink text-ink", soft: "bg-pink-100", text: "text-pink" },
};
