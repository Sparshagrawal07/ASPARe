import Link from "next/link";
import { Wordmark } from "./Logo";

export function Footer() {
  return (
    <footer className="mt-24 border-t-2 border-ink bg-ink text-paper">
      <div className="mx-auto grid max-w-6xl gap-10 px-5 py-14 md:grid-cols-[1.5fr_1fr_1fr]">
        <div>
          <div className="[&_*]:!text-paper"><Wordmark /></div>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-paper/70">
            Cloud storage security that detects, explains, fixes and proves. For AWS today, Azure and Google Cloud next.
          </p>
        </div>
        <div>
          <h2 className="font-display text-base font-bold">Product</h2>
          <ul className="mt-3 space-y-2 text-sm text-paper/70">
            <li><Link className="hover:text-sun" href="/demo">Try the demo</Link></li>
            <li><Link className="hover:text-sun" href="/sign-up">Start free</Link></li>
            <li><Link className="hover:text-sun" href="/connect">How it connects</Link></li>
            <li><Link className="hover:text-sun" href="/trust">Trust and safety</Link></li>
          </ul>
        </div>
        <div>
          <h2 className="font-display text-base font-bold">Our promise</h2>
          <p className="mt-3 text-sm leading-relaxed text-paper/70">
            ASPARe never stores cloud keys. Access is a role you create and can delete at any moment, read-only unless you opt in to fixes.
          </p>
        </div>
      </div>
      <div className="border-t border-paper/15 py-5 text-center text-xs text-paper/60">
        ASPARe is a university project built as a working product. Claims here say what was verified and what was not.
      </div>
    </footer>
  );
}
