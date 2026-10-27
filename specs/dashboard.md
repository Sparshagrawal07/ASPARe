# ASPARe Dashboard — Component Specifications

**Source of truth for design tokens:** `DESIGN.md` (read first)  
**Implementable with:** Streamlit native components + one `st.markdown(unsafe_allow_html=True)` style block  
**Constraint:** No backend Python logic changes. Dashboard UI only.

---

## 0. Global shell (applies to all sections)

- `st.set_page_config(page_title="ASPARe Dashboard", layout="wide", initial_sidebar_state="collapsed")`
- Existing style block extended with new classes (see DESIGN.md §7).
- Sidebar (existing): "Recorded estate" kicker, bucket count, CloudTrail event metric, data-class chip list, bucket list expander. Keep unchanged; optional: add a compact pipeline status chip row.
- Main content width: `max-width: 1400px`, `padding-top: 1.4rem`.

---

## 1. Hero / header section

**Position:** Top of main content, above metrics.

### 1.1 Kicker
- Text: `ASPARe · Automated Security Posture Assessment & Remediation`
- Class: `.hero-kicker` (existing): uppercase, 0.76rem, letter-spacing 0.14em, color `#8b9bb4`.
- Purpose: brands the page without competing with the title.

### 1.2 Title
- Text: `Cloud storage security, explained`
- Type: `st.title` → maps to `--text-display` (clamp 1.75–2.5rem, weight 700, letter-spacing `-0.02em`).
- Color: `--color-ink` (`#f1f5f9`).

### 1.3 Narrative subcopy
- Text (existing, keep): "Each finding answers three questions: **what is wrong**, **how that hurts**, and **what the remedy does**. The lab replays a recorded CloudTrail / S3 estate. It does not call a live AWS account."
- Type: `st.write`, `--text-body` (0.95rem, line-height 1.5), max width 75ch.
- Color: `--color-ink-muted` (`#94a3b8`) acceptable here since it's supporting copy; ensure ≥4.5:1 against bg.

### 1.4 "Helping people" narrative strip (NEW)
A single full-width strip below the narrative that frames the human stakes.

- Layout: `st.container` with light border (`--color-border`) and subtle surface fill (`--color-surface`), padding 1rem.
- Left: bold label `What's being protected` (0.85rem, `--color-accent`).
- Right: dynamic human-impact sentence (e.g., "ASPARe protects student records, patient health data, and payroll across N buckets in the campus estate."), `--color-ink`.
- CTA link (text only, no button): `View data inventory →` in `--color-accent`.
- Responsive: full width on all breakpoints; text wraps, never truncates.

---

## 2. Metrics cards

**Position:** Directly below the hero strip, one row.

**Layout:** `st.columns(6)`, each `width="stretch"`, equal height.

| # | Label | Value source | Semantic color (delta) | Delta / note |
|---|-------|--------------|------------------------|--------------|
| 1 | Buckets in estate | `len(buckets)` | neutral (`off`) | none |
| 2 | Findings | `snapshot.total_findings` | warning if >0 (`inverse`) | none |
| 3 | Critical | `snapshot.critical_findings` | error (`inverse`) | none |
| 4 | High | `snapshot.high_findings` | warning (`inverse`) | none |
| 5 | Remedies verified | `snapshot.successful_remediations` | success (`normal`) | none |
| 6 | Failed remedies | `snapshot.failed_remediations` | error (`inverse`) | none |

**Styling notes:**
- `st.metric` value = large number (`--text-display`-ish via Streamlit default metric sizing).
- Label = small, `--color-ink-faint`.
- `delta_color`: `"normal"` (green) for verified, `"inverse"` (red) for critical/high/failed, `"off"` (gray) for neutral counts.
- No gradient backgrounds, no "hero-metric" cliché — functional metric cards only.
- Accessibility: each metric's label is visible text (not icon-only), so screen readers get context.

---

## 3. Charts

**Position:** Full-width row(s) below metrics.

### 3.1 Severity distribution bar chart
- Type: `st.bar_chart`
- Data: severity → count (CRITICAL, HIGH, MEDIUM, LOW).
- X: severity; Y: count.
- Colors: severity token hex (CRITICAL `#f87171`, HIGH `#fb923c`, MEDIUM `#f59e0b`, LOW `#94a3b8`).
- Title (caption above): `Findings by severity` (0.85rem, `--color-ink-faint`).
- No legend needed (x-axis labels are the categories).
- Accessibility: provide `st.caption` summary: "N findings total — X critical, Y high."

### 3.2 Remediation success rate
- Type: `st.area_chart` or `st.bar_chart` (single series or two bars: verified vs failed).
- Data: `successful_remediations`, `failed_remediations`.
- Colors: success `#34d399`, error `#f87171`.
- Title: `Remediation outcome` (0.85rem, `--color-ink-faint`).
- Optional: show rate as a `st.metric` beside the chart ("92% verified") — but only if aggregator exposes it (see api-contract).

### 3.3 Data class breakdown (bucket count per DataClass)
- Type: `st.bar_chart`
- Data: DataClass → bucket count (from inventory, sorted desc).
- Colors: data-class token hues (DESIGN.md table).
- Title: `Buckets by data class` (0.85rem, `--color-ink-faint`).
- Highlight sensitive classes (FERPA, PHI, FINANCIAL, PII, SECRETS) with full opacity; non-sensitive (PUBLIC, INTERNAL, BACKUP, AUDIT) at 60% opacity to direct attention to human-impact classes.
- Accessibility: caption summarizing top sensitive class and count.

### 3.4 Layout
- Desktop (≥1100px): 3 columns (severity, remediation, data-class), each chart `width="stretch"`.
- Mobile/narrow: charts stack vertically in source order (severity → remediation → data-class).
- All charts use Streamlit default theme (dark) — do not override to light.

---

## 4. Human impact section

**Position:** Full-width section below charts, above tabs.

**Purpose:** Answer "who does this protect?" — the "helping people" narrative. Maps DataClass tags to human-readable impact statements.

### 4.1 Section header
- Kicker: `Human impact` (uppercase, tracked, `--color-accent`, 0.76rem).
- Heading: `What's being protected across the estate` (`--text-section`, 1.25rem, weight 600).
- Subcopy (1–2 sentences): "Each bucket carries a DataClass tag. ASPARe shows how many buckets of each sensitive class are in the estate, and what the human impact would be if that data were exposed." (`--text-body`, max 75ch).

### 4.2 Impact cards
**Layout:** `st.columns(n)` wrapping. Max 5 cards per row; below ~1100px, fewer per row via Streamlit stacking. Each card `width="stretch"`.

**Card structure (`.impact-card`):**
- Top-left: small accent dot (8px circle) in the data-class hue.
- Top-right: DataClass badge (`.badge`, 0.72rem, weight 700, letter-spacing 0.04em) — text white on class-hue dark tint, or dark text on light class hue if contrast allows.
- Center: bucket count (large, `--text-display`-adjacent via `st.metric`-style or `st.markdown` big number) + label `buckets`.
- Bottom: human-impact statement (0.85rem, `--color-ink`, 2 lines max).
- Border: 1px `--color-border`, border-radius 12px (max per impeccable card rule), fill `--color-surface`.

**Data-class → human impact map:**

| DataClass | Bucket count source | Human-impact statement |
|-----------|---------------------|------------------------|
| FERPA | count of `tags.DataClass == "FERPA"` | "Protecting student transcripts, enrollment, and financial-aid records." |
| PHI | count of `tags.DataClass == "PHI"` | "Protecting patient clinic visits and consent records." |
| FINANCIAL | count of `tags.DataClass == "FINANCIAL"` | "Protecting payroll and tax batch records." |
| PII | count of `tags.DataClass == "PII"` | "Protecting student IDs, HR, and housing records." |
| SECRETS | count of `tags.DataClass == "SECRETS"` | "Protecting infrastructure credentials and deployment artifacts." |

**Ordering:** Sensitive classes first (FERPA, PHI, FINANCIAL, PII, SECRETS), then others (AUDIT, BACKUP, LEGAL, SENSITIVE, INTERNAL, PUBLIC) if space allows. Classes with 0 buckets are hidden entirely.

**Card count:** Show top 5 sensitive classes with count > 0. If fewer than 5 have count > 0, show only those. Never render empty cards.

### 4.3 Protected vs exposed summary (optional strip)
- One line: "N of M sensitive-class buckets have all critical controls (public access block, encryption) in place." — only if aggregator can compute (see api-contract `data_class_breakdown` with protected flag).

---

## 5. Issues tab — before/after state visualization

**Existing tab:** `Issues — What / How / Remedy` (keep title).

### 5.1 Empty state
- `st.info`: "No findings yet. Click **Load estate**, then **Detect findings**."
- No chart, no cards — just the info.

### 5.2 Filters (existing, keep)
- 3 columns: Severity multiselect, Status multiselect, Control (rule) multiselect. Defaults = all selected.
- Caption: `Showing N of M findings`.

### 5.3 Per-resource issue card (existing `issue-card` enhanced)
Structure per `FindingRow`:
- Badge row: severity badge (`.sev-{SEV}`) + status badge (`.st-{STATUS}`) + `<code>{resource}</code>` + rule title.
- What/How/Remedy 3-column grid (existing `.how-grid`, collapses to 1 col <1100px).
- **NEW — Before/After chips:** When remediated, show two chips side by side:
  - `Before: {posture_lines(before_state) joined}` vs `After: {posture_lines(after_state) joined}`.
  - Visual: `Before` chip in `--color-ink-faint` tint, `After` chip in `--color-success` tint. Changed controls highlighted (e.g., bold the flag that flipped).
  - Implement as two `st.columns(2)` with `st.caption` (existing pattern) but wrapped in bordered containers with class-tinted fills.
- Standards + detected_at caption (existing).

### 5.4 Grouping
- Group by `resource`, expanders per resource, worst severity as expander header label (existing behavior).

### 5.5 Accessibility
- Badges have visible text labels (not color-only meaning).
- Before/after uses text + tint (not color alone) to indicate change.

---

## 6. Estate tab — enhanced dataframe with data class grouping

**Existing tab:** `Estate`.

### 6.1 Intro line
- `st.write`: "Every bucket below came from the recorded inventory. Open a row in **Issues** to see why it failed." (keep).

### 6.2 Table columns (existing + enhancements)
| Column | Source | Enhancement |
|--------|--------|-------------|
| Bucket | `item["name"]` | monospace, `--color-ink` |
| Data class | `tags.DataClass` | chip styled with data-class hue (`.badge`) |
| Purpose | `tags.Purpose` | text |
| Env | `tags.Environment` | text (chip: prod=neutral, dev/lab=muted) |
| Findings | count | number |
| Critical | count | red tint if >0 |
| Fixed | count | green tint if >0 |
| Alerts | count | blue tint if >0 |

**Styling:** Streamlit `st.dataframe` does not support per-cell CSS classes directly. Implement data-class as a separate chip column only if feasible via `st.column_config`; otherwise keep plain text and rely on the data-class color in the human-impact section. Do not hack HTML into dataframe cells.

### 6.3 Grouping view (optional)
- Add a `st.selectbox`: "Group by" → options: None, Data Class, Environment, Purpose.
- When grouped, show a subheader per group (data class name + hue dot + bucket count), then the filtered rows below. This surfaces the human-impact grouping directly in the estate view.

---

## 7. Pipeline flow — Detect → Classify → Remediate → Verify → Audit

**Position:** Full-width section above the tabs (persistent narrative backbone) — OR its own tab. Recommendation: persistent section above tabs so progress is visible regardless of active tab.

### 7.1 Layout
- 5 steps horizontally: `st.columns(5)`, each `width="stretch"`.
- Connector: right arrow (`→`) between steps, rendered as `st.markdown` centered text or a thin border line on the column's right edge. On narrow screens, stack vertically with vertical connectors.

### 7.2 Step structure (`.pipeline-step`)
Each step:
- Number badge: `1`…`5` (0.75rem, weight 700, on accent or neutral fill).
- Title: `Detect` / `Classify` / `Remediate` / `Verify` / `Audit` (0.85rem, weight 600).
- Description: one-line purpose (0.78rem, `--color-ink-muted`):
  - Detect: "Inspect every bucket against the policy knowledge base."
  - Classify: "Map findings to CRITICAL / HIGH / MEDIUM risk decisions."
  - Remediate: "Auto-apply approved fixes (CRITICAL/HIGH only)."
  - Verify: "Re-inspect after each write — a Put* response is not success."
  - Audit: "Record every action to the immutable audit trail."
- Status chip (right-aligned within step): `PENDING` / `ACTIVE` / `COMPLETE` (`.badge`, 0.68rem).
  - PENDING: neutral fill `#1e293b`, text `#cbd5e1`.
  - ACTIVE: accent fill `#22d3ee`, text `#0f172a`.
  - COMPLETE: success fill `#103226`, text `#6ee7b7`.

### 7.3 Progress indicator
- `st.progress` above or below the steps, value = fraction of stages complete (0.0 / 0.25 / 0.5 / 0.75 / 1.0), mapped from `st.session_state.step`:
  - idle → 0.0, loaded → 0.25, detected → 0.5, remediated → 0.75 (verify/audit are audit-trail writes, already recorded), remediated+audit → 1.0.
- Label: none (progress bar is decorative; status chips carry meaning).

### 7.4 Step-to-session mapping
| Step | Session condition for COMPLETE |
|------|-------------------------------|
| Detect | `step == "detected"` or `step == "remediated"` |
| Classify | `step == "detected"` or `step == "remediated"` (risk evaluation happens at detection) |
| Remediate | `step == "remediated"` |
| Verify | `step == "remediated"` (verification is part of remediate run) |
| Audit | always COMPLETE once any record exists (audit trail is append-only) |

---

## 8. Remedy log tab — activity timeline

**Existing tab:** `Remedy log`.

### 8.1 Empty state
- `st.info`: "No remediations yet. After detection, click **Apply auto-remedies**."

### 8.2 Timeline entries (one per `ActivityRow`)
Each entry in an `st.expander` (existing), label: `{resource} · {remedy_name} · {result}`.

**Inside each expander:**
- Action: `<code>{action}</code>` (0.85rem, monospace).
- Message: `row.message` or explainer `remedy_does` (`--text-body`).
- Leaves: explainer `remedy_leaves` (`--color-ink-muted`, caption).
- Before/After: two columns (`st.columns(2)`):
  - Left: `**Before**` + `posture_lines(before_state)` as bullets.
  - Right: `**After**` + `posture_lines(after_state)` or "n/a".
- Footer caption: `Verified: {yes/no} · {timestamp}` (`.muted`, 0.78rem).

### 8.3 Result badge
- Add a small status chip to each expander header: `Verified` (success) / `Failed` (error) based on `row.verified`.
- Colors: verified = `#6ee7b7` on `#103226`; failed = `#fca5a5` on `#450a0a`.

### 8.4 Ordering
- Reverse chronological (newest first) — existing behavior, keep.

---

## 9. States & edge cases (all sections)

| State | Treatment |
|-------|-----------|
| Lab not loaded | Hero narrative + metrics show zeros/disabled; "Load estate" button primary; charts show empty; info message in Issues/Remedy log. |
| No findings | Metrics zero; severity chart empty; data-class chart shows all buckets (still useful); Issues shows empty-state info. |
| All remediated | Critical/High metrics = 0; verified metric = total; pipeline shows COMPLETE; Remedy log shows all entries verified. |
| Failed remediation | Failed metric > 0; that activity entry shows `Verified: no`; pipeline Verify step may show ACTIVE/needs-attention (per aggregator). |
| Zero buckets of a data class | That impact card is hidden (not rendered as "0 buckets"). |

---

## 10. Accessibility checklist (WCAG 2.1 AA)

- [ ] All color meaning reinforced with text (badges, chips, status).
- [ ] Body text ≥ 4.5:1 against `--color-bg` (`#0f172a`).
- [ ] Badge text passes ≥4.5:1 against its dark badge background.
- [ ] No text relies on `letter-spacing < -0.02em` at display sizes.
- [ ] `st.metric` labels are visible (screen-reader accessible).
- [ ] Charts accompanied by `st.caption` text summaries.
- [ ] Expanders have descriptive labels (resource + rule + count).
- [ ] Keyboard-navigable (Streamlit native; no custom JS focus management).
- [ ] Reduced motion respected (no CSS animations beyond Streamlit defaults).
