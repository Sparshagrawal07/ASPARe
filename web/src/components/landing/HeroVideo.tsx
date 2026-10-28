"use client";

import { Pause, Play } from "lucide-react";
import { useEffect, useRef, useState } from "react";

/**
 * The ASPARe showreel: 15 seconds assembled from the site's real components and the live engine's real output.
 * Autoplays muted and looped, pauses when scrolled away, and does not autoplay for people who prefer reduced motion.
 */
export function HeroVideo() {
  const ref = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const reduced = useRef(false);

  useEffect(() => {
    const video = ref.current;
    if (!video) return;
    reduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const sync = () => setPlaying(!video.paused);
    video.addEventListener("play", sync);
    video.addEventListener("pause", sync);
    const io = new IntersectionObserver(
      ([entry]) => {
        if (reduced.current) return;
        if (entry.isIntersecting) void video.play().catch(() => undefined);
        else video.pause();
      },
      { threshold: 0.35 },
    );
    io.observe(video);
    return () => {
      io.disconnect();
      video.removeEventListener("play", sync);
      video.removeEventListener("pause", sync);
    };
  }, []);

  function toggle() {
    const video = ref.current;
    if (!video) return;
    reduced.current = true; // an explicit choice beats scroll-based autoplay
    if (video.paused) void video.play().catch(() => undefined);
    else video.pause();
  }

  return (
    <figure className="relative mx-auto w-full max-w-[640px] lg:mx-0" aria-label="ASPARe showreel">
      <div className="card relative -rotate-1 overflow-hidden bg-white p-0">
        <video
          ref={ref}
          className="block aspect-video w-full"
          src="/showreel/aspare-showreel.mp4"
          poster="/showreel/aspare-showreel-poster.jpg"
          width={1280}
          height={720}
          muted
          loop
          playsInline
          preload="metadata"
          aria-describedby="showreel-desc"
        />
        <button
          type="button"
          onClick={toggle}
          aria-label={playing ? "Pause the showreel" : "Play the showreel"}
          className="btn absolute bottom-3 right-3 h-11 w-11 bg-white !shadow-[3px_3px_0_0_#1c1b3a]"
        >
          {playing ? <Pause size={18} aria-hidden="true" /> : <Play size={18} aria-hidden="true" />}
        </button>
      </div>
      <figcaption className="absolute -right-2 -top-5 rotate-3 rounded-xl border-2 border-ink bg-sun px-3 py-1.5 text-sm font-extrabold shadow-pop">
        Made from the real product
      </figcaption>
      <p id="showreel-desc" className="sr-only">
        A fifteen second showreel. A simulated cloud estate is misconfigured, ASPARe finds fourteen findings, explains why it
        auto-fixes a sensitive bucket but holds a public marketing site for a human, then fixes and verifies the change by
        re-reading the cloud.
      </p>
    </figure>
  );
}
