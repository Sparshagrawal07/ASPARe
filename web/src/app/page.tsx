import { Clouds } from "@/components/landing/Clouds";
import { CtaBand } from "@/components/landing/CtaBand";
import { Features } from "@/components/landing/Features";
import { Hero } from "@/components/landing/Hero";
import { Marquee } from "@/components/landing/Marquee";
import { Steps } from "@/components/landing/Steps";
import { WhyHeld } from "@/components/landing/WhyHeld";

export default function Home() {
  return (
    <>
      <Hero />
      <Marquee />
      <Steps />
      <Features />
      <WhyHeld />
      <Clouds />
      <CtaBand />
    </>
  );
}
