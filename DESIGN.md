# ASPARe Dashboard — Design Specification

**Product:** ASPARe — Automated Security Posture Assessment & Remediation Engine  
**Surface:** Streamlit dashboard (`dashboard/app.py`) — dark theme, Python-native  
**Status:** Design direction (specs only — no implementation code)  
**Audience:** @frontend / Streamlit developer implementing from these specs

---

## 1. Design rationale

### Physical scene (why dark mode)
A security operator or compliance reviewer sits at a desk under typical indoor fluorescent/LED ambient light, reviewing the campus S3 estate over a multi-step session. They need to scan severity at a glance, understand the human stakes (student records, patient data, financial records), and follow the Detect → Classify → Remediate → Verify → Audit story. Dark mode reduces eye strain for long review sessions and matches the existing slate/navy aesthetic.

### Color strategy: Restrained
A dark slate/navy base with tinted-neutral surfaces and one brand accent (cyan/blue) used ≤10% of surface area. Severity and status carry their own semantic colors (red/orange/amber/green/blue) but only on badges, chips, and chart marks — never as page backgrounds. This avoids:
- the "SaaS-cream" warm-neutral body background (impeccable absolute ban)
- the "navy-and-gold fintech" reflex
- gradient text, glassmorphism as default, side-stripe borders, and identical card grids

### Typography
Single sans-serif family (Inter / system UI) in multiple weights. No display letter-spacing tighter than `-0.02em`. Body line length capped at 65–75ch for prose blocks.

### Layout
- Flexbox for 1D rows (metrics, badge rows, timeline).
- CSS grid only where 2D alignment is genuinely needed (the What/How/Remedy three-column grid).
- No nested cards. Cards used only for metric cards and human-impact cards — where they're genuinely the best affordance.
- Semantic z-index scale; no arbitrary `999`/`9999`.

### Motion
Streamlit-native. No CSS layout-property animation. Entrance crossfades only where Streamlit supports them; honors reduced-motion preferences implicitly through Streamlit.

---

## 2. Color tokens

All tokens defined in OKLCH with hex fallbacks for Streamlit's native components (`st.metric`, `st.bar_chart`) which accept hex/CSS color strings.

### Base palette

| Token | OKLCH | Hex (fallback) | Role |
|-------|-------|----------------|------|
| `--color-bg` | `oklch(0.11 0.015 240)` | `#0f172a` | Page background (slate-900) |
| `--color-surface` | `oklch(0.15 0.015 240)` | `#1e293b` | Card / container surface (slate-800) |
| `--color-surface-hover` | `oklch(0.19 0.015 240)` | `#334155` | Hovered surface (slate-700) |
| `--color-border` | `oklch(0.22 0.01 240)` | `#475569` | Subtle dividers (slate-600) |
| `--color-ink` | `oklch(0.96 0.01 240)` | `#f1f5f9` | Primary body text (slate-100) |
| `--color-ink-muted` | `oklch(0.62 0.01 240)` | `#94a3b8` | Secondary / caption text (slate-400) |
| `--color-ink-faint` | `oklch(0.42 0.01 240)` | `#64748b` | De-emphasized labels (slate-500) |
| `--color-accent` | `oklch(0.68 0.14 200)` | `#22d3ee` | Brand accent — cyan (≤10% of surface) |
| `--color-accent-inverse` | `oklch(0.11 0.015 240)` | `#0f172a` | Text on accent |

### Semantic / status colors (dark-bg safe)

| Token | OKLCH | Hex | Role |
|-------|-------|-----|------|
| `--color-success` | `oklch(0.78 0.14 155)` | `#34d399` | Remediated / verified / fixed |
| `--color-warning` | `oklch(0.82 0.15 70)` | `#fbbf24` | Alert / medium / attention |
| `--color-error` | `oklch(0.72 0.17 25)` | `#f87171` | Critical / failed / error |
| `--color-info` | `oklch(0.76 0.15 215)` | `#60a5fa` | Info / neutral / detected |

### Severity badges (dark background + light text)

| Severity | BG token | BG hex | Text token | Text hex |
|----------|----------|--------|------------|----------|
| CRITICAL | `oklch(0.30 0.11 25)` | `#7f1d1d` | `#fca5a5` | `#fca5a5` |
| HIGH | `oklch(0.30 0.11 55)` | `#92400e` | `#fdba74` | `#fdba74` |
| MEDIUM | `oklch(0.30 0.10 65)` | `#713f12` | `#fcd34d` | `#fcd34d` |
| LOW | `oklch(0.30 0.06 240)` | `#1e293b` | `#94a3b8` | `#94a3b8` |

### Status badges

| Status | BG | Text |
|--------|----|------|
| REMEDIATED | `#103226` (emergent green-dark) | `#6ee7b7` |
| ALERT_AND_LOG | `#1e293b` (slate-800) | `#93c5fd` |
| AUTO_REMEDIATE | `#2a1840` (purple-dark) | `#d8b4fe` |
| VERIFIED | `#103226` | `#6ee7b7` |
| FAILED | `#450a0a` | `#fca5a5` |
| PENDING | `#1e293b` | `#cbd5e1` |

### Data-class colors (human impact cards + estate grouping)

Each DataClass gets a distinct hue for its impact card + chart segment. Hues are spaced so adjacent classes remain distinguishable on dark bg.

| DataClass | Hue (deg) | Hex | Human theme |
|-----------|-----------|-----|-------------|
| FERPA | 210 (blue) | `#60a5fa` | Student records |
| PHI | 340 (rose) | `#fb7185` | Patient health data |
| FINANCIAL | 35 (amber) | `#f59e0b` | Financial / payroll |
| PII | 260 (purple) | `#a78bfa` | Personal identity |
| AUDIT | 210 (slate) | `#94a3b8` | Audit / log trails |
| BACKUP | 170 (teal) | `#2dd4bf` | Backup / recovery |
| LEGAL | 240 (indigo) | `#6366f1` | Legal / e-discovery |
| SECRETS | 330 (fuchsia) | `#c084fc` | Secrets / credentials |
| SENSITIVE | 25 (orange) | `#fb923c` | Sensitive / quarantined |
| INTERNAL | 190 (cyan) | `#22d3ee` | Internal operations |
| PUBLIC | 135 (green) | `#4ade80` | Public-facing assets |

### Contrast requirements (WCAG 2.1 AA)
- Body text ≥ 4.5:1 against background; large/bold text ≥ 3:1.
- On `--color-bg` (`#0f172a`), `--color-ink` (`#f1f5f9`) passes; `--color-ink-muted` (`#94a3b8`) must be reserved for captions/labels only, never body copy.
- Badge text is always the light variant against its dark badge background.

---

## 3. Typography

| Token | Size | Weight | Line-height | Letter-spacing | Use |
|-------|------|--------|-------------|----------------|-----|
| `--text-display` | clamp(1.75rem, 4vw, 2.5rem) | 700 | 1.15 | `-0.02em` | Page title (H1) |
| `--text-section` | 1.25rem | 600 | 1.3 | `-0.01em` | Section headings (H2/H3) |
| `--text-body` | 0.95rem | 400 | 1.5 | 0 | Body prose |
| `--text-small` | 0.85rem | 400 | 1.45 | 0.01em | Captions, meta |
| `--text-badge` | 0.72rem | 700 | 1 | 0.04em | Badges, chips |
| `--text-kicker` | 0.76rem | 600 | 1 | 0.14em | Section eyebrow (uppercase) |

Rules:
- Display letter-spacing floor: `-0.02em` (never tighter — cramped letters read as "designed by AI").
- One font family only (Inter / system-ui). Do not pair two similar sans-serifs.
- `text-wrap: balance` on H1–H3; `text-wrap: pretty` on long prose.
- Body prose max width: 65–75ch.

---

## 4. Layout & spacing

### Spacing scale (px / rem)

| Token | Value | Use |
|-------|-------|-----|
| `--space-xs` | 0.25rem (4px) | Tight internal padding |
| `--space-sm` | 0.5rem (8px) | Component gaps |
| `--space-md` | 1rem (16px) | Section padding, card padding |
| `--space-lg` | 1.5rem (24px) | Between major sections |
| `--space-xl` | 2rem (32px) | Page-level vertical rhythm |

### Grid rules
- **Metrics row**: `st.columns(6)` — equal-width metric cards.
- **Charts row**: `st.columns(2)` or `st.columns(3)` depending on chart count; charts stack vertically below 1000px.
- **What/How/Remedy**: 3-column CSS grid (`grid-template-columns: 1fr 1fr 1fr`), collapses to 1 column below ~1100px (matches existing `.how-grid` media query).
- **Human impact**: single row of cards wrapping via `st.columns(n)` where n = number of sensitive classes shown (max 5 per row), wraps below ~1100px.
- **Pipeline**: horizontal 5-step flow with connector lines; wraps to vertical stack on narrow screens.
- **Responsive**: no custom breakpoints beyond the existing 1100px media query; rely on `st.columns` stacking behavior and `width="stretch"`.

### Card usage (impeccable ban: cards are not the default)
Cards permitted only for:
1. Metric cards (number + label + optional delta).
2. Human-impact data-class cards (bucket count + impact statement).
Not for: issue detail (use the existing `issue-card` border pattern), general content containers, or nested groupings.

---

## 5. Component map (Streamlit-native)

| Component | Streamlit primitive | Custom CSS class | Notes |
|-----------|---------------------|------------------|-------|
| Page shell | `st.set_page_config(layout="wide")` | `.block-container` | `max-width: 1400px`, `padding-top: 1.4rem` |
| Kicker | `st.markdown(unsafe_allow_html=True)` | `.hero-kicker` | Uppercase, tracked, muted |
| Hero title | `st.title` | — | `--text-display` |
| Hero narrative | `st.write` / `st.markdown` | — | `--text-body`, max 75ch |
| Metric card | `st.metric` | — | Label + value + optional delta; color via delta |
| Severity badge | `st.markdown(unsafe_allow_html=True)` | `.badge .sev-{SEV}` | Existing pattern, keep |
| Status badge | `st.markdown(unsafe_allow_html=True)` | `.badge .st-{STATUS}` | Existing pattern, keep |
| Human-impact card | `st.container` + `st.markdown` | `.impact-card` | Border + fill tint + data-class accent dot |
| Bar chart | `st.bar_chart` | — | Altair/Vega-Lite under the hood; use token colors |
| Area chart | `st.area_chart` | — | Remediation rate trend |
| Dataframe | `st.dataframe` | — | `width="stretch"`, `hide_index=True` |
| Tabs | `st.tabs` | — | Issues, Estate, Pipeline, Remedy log |
| Expander | `st.expander` | — | Per-resource issue detail |
| Divider | `st.divider` | — | Section separation |
| Caption | `st.caption` | `.muted` | Meta, sources, timestamps |
| Button | `st.button` | — | Primary = accent; secondary = outline |
| Progress | `st.progress` | — | Pipeline completion |
| Pipeline step | `st.columns(5)` + `st.markdown` | `.pipeline-step` | Icon + title + status chip |

---

## 6. Design rules recap (impeccable alignment)

**Never:**
- Side-stripe borders (`border-left`/`border-right` > 1px as colored accent).
- Gradient text (`background-clip: text` + gradient).
- Glassmorphism as default.
- Hero-metric template (big number + small label + gradient accent) as the *only* metric treatment — metrics here are functional, not decorative.
- Identical card grids repeated endlessly.
- Tiny uppercase tracked eyebrow above *every* section — one named kicker only.
- Numbered section markers (01/02/03) as default scaffolding.
- `border: 1px` + `box-shadow` blur ≥16px on the same element (ghost-card).
- `border-radius: 32px+` on cards — cards top out at 12–16px; pills only for tags/buttons.
- Sketchy/hand-drawn SVG illustrations.
- `repeating-linear-gradient` stripe backgrounds.
- Decorative CSS grid backgrounds.
- Text overflowing containers at any breakpoint.

**Always:**
- Verify contrast ≥4.5:1 body / ≥3:1 large.
- Honor reduced motion.
- Use one font family in multiple weights.
- Keep line length 65–75ch for prose.
- Vary spacing for rhythm; don't default every section to identical padding.

---

## 7. Streamlit implementation notes (for the developer)

- All custom styling lives in a single `st.markdown(unsafe_allow_html=True)` style block, extending the existing one. Add new classes: `.impact-card`, `.impact-accent`, `.pipeline-step`, `.pipeline-connector`, `.human-impact-grid`.
- `st.metric` does not support arbitrary background colors; use the `delta`/`delta_color` parameter for semantic coloring (normal=green, inverse=red, off=gray). The metric *label* carries the semantic meaning; the value stays neutral ink.
- `st.bar_chart`/`st.area_chart` accept a `color` parameter for discrete series; map severity/data-class to the token hex values above.
- `st.columns(n)` with `width="stretch"` gives responsive stacking; no custom media queries needed beyond the existing 1100px rule.
- Do not alter `src/aspare/reporting/*.py` backend logic. New dashboard-only aggregator helper methods (see `api-contract.md`) are additive and read-only.
- Keep the existing dark theme; do not introduce a light-mode toggle.
