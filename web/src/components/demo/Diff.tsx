export function Diff({ lines, other, tone }: { lines: string[]; other: string[]; tone: "before" | "after" }) {
  const changed = (l: string) => !other.includes(l);
  return (
    <>
      {lines.map((l) => (
        <p key={l} className={changed(l) ? (tone === "before" ? "font-bold text-bad line-through" : "font-bold text-ok") : "text-muted/70"}>
          {changed(l) ? (tone === "before" ? "- " : "+ ") : ""}
          {l}
        </p>
      ))}
    </>
  );
}
