"""ASPARe dashboard — What happened, how it hurts, what the remedy did."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from aspare.audit.repository import JsonlAuditRepository, S3AuditRepository
from aspare.core.enums import RiskDecision
from aspare.dataset import detect, load_events, load_inventory, remediate, start_lab, stop_lab
from aspare.live import LiveConnectionError, LiveSession, approval_gate, approve, connect, scan
from aspare.providers.aws.client import s3_client
from aspare.reporting.aggregator import (
    HUMAN_IMPACT_MAP,
    FindingRow,
    ReportingAggregator,
)
from aspare.reporting.explainers import explainer_for, posture_lines

st.set_page_config(page_title="ASPARe Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
      .block-container { padding-top: 1.4rem; max-width: 1400px; }
      .hero-kicker { letter-spacing: 0.14em; text-transform: uppercase; font-size: 0.76rem; color: #8b9bb4; }
      .issue-card { border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 1rem 1.1rem 0.4rem; margin-bottom: 0.85rem; background: rgba(15,23,42,0.35); }
      .badge { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 999px; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; }
      .sev-CRITICAL { background: #3f1212; color: #ff8a8a; }
      .sev-HIGH { background: #3f2412; color: #ffb070; }
      .sev-MEDIUM { background: #3f3612; color: #f5d56a; }
      .st-REMEDIATED { background: #103226; color: #6ee7b7; }
      .st-ALERT_AND_LOG { background: #1e293b; color: #93c5fd; }
      .st-AUTO_REMEDIATE { background: #2a1840; color: #d8b4fe; }
      .how-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.8rem; margin-top: 0.85rem; }
      @media (max-width: 1100px) { .how-grid { grid-template-columns: 1fr; } }
      .how-box { border-radius: 12px; padding: 0.85rem 0.95rem; min-height: 8.5rem; }
      .how-what { background: rgba(56,189,248,0.08); border: 1px solid rgba(56,189,248,0.22); }
      .how-hurt { background: rgba(251,146,60,0.08); border: 1px solid rgba(251,146,60,0.22); }
      .how-fix { background: rgba(52,211,153,0.08); border: 1px solid rgba(52,211,153,0.22); }
      .how-box h4 { margin: 0 0 0.4rem 0; font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
      .how-box p { margin: 0; font-size: 0.92rem; line-height: 1.45; }
      .muted { color: #94a3b8; font-size: 0.88rem; }
      /* New classes (DESIGN.md §7) */
      .human-strip { border: 1px solid #475569; border-radius: 12px; background: rgba(30,41,59,0.6); padding: 1rem; display: flex; align-items: center; gap: 1rem; }
      .strip-label { color: #22d3ee; font-weight: 700; font-size: 0.85rem; white-space: nowrap; }
      .strip-body { color: #f1f5f9; font-size: 0.95rem; line-height: 1.45; }
      .strip-cta { color: #22d3ee; font-size: 0.85rem; margin-left: auto; text-decoration: none; white-space: nowrap; }
      .impact-card { border: 1px solid #475569; border-radius: 12px; padding: 1rem 1.1rem; background: rgba(30,41,59,0.6); }
      .impact-accent { display: inline-block; width: 8px; height: 8px; border-radius: 50%; }
      .pipeline-step { text-align: center; line-height: 1.4; }
      .pipeline-connector { color: #94a3b8; font-size: 1.1rem; }
      .chip-box { border: 1px solid #475569; border-radius: 8px; padding: 0.5rem 0.75rem; background: rgba(30,41,59,0.4); }
      .st-PENDING { background: #64748b; color: #0f172a; }
      .st-ACTIVE { background: #22d3ee; color: #0f172a; }
      .st-COMPLETE { background: #103226; color: #6ee7b7; }
      .st-VERIFIED { background: #103226; color: #6ee7b7; }
      .st-FAILED { background: #450a0a; color: #fca5a5; }
      .human-impact-grid { display: flex; flex-wrap: wrap; gap: 1rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

if "lab" not in st.session_state:
    st.session_state.lab = None
if "findings" not in st.session_state:
    st.session_state.findings = []
if "step" not in st.session_state:
    st.session_state.step = "idle"

with st.sidebar:
    mode = st.radio(
        "Data source",
        ["Recorded lab", "Live AWS"],
        help="Recorded lab replays a captured estate against a mocked S3. Live AWS scans your real account "
        "read-only and remediates only what you approve.",
    )
live_mode = mode == "Live AWS"
if st.session_state.get("mode_prev") not in (None, mode):
    stop_lab(st.session_state.lab)  # moto patches boto3 globally; never leave it active for live calls
    st.session_state.lab = None
    st.session_state.findings = []
    st.session_state.step = "idle"
st.session_state.mode_prev = mode
if "live" not in st.session_state:
    st.session_state.live = None
live: LiveSession | None = st.session_state.live if live_mode else None

if live_mode:
    inventory = live.inventory if live else {"buckets": [], "source": "Not connected"}
    events: list = []
else:
    inventory = load_inventory()
    events = load_events()
buckets = inventory.get("buckets") or []


def _audit_repo():
    if live_mode:
        path = Path(live.audit_path if live else os.environ.get("ASPARE_LIVE_AUDIT_PATH", "var/audit/live.jsonl"))
        return JsonlAuditRepository(path), str(path)
    backend = os.environ.get("ASPARE_AUDIT_BACKEND", "jsonl")
    if backend == "s3":
        bucket = os.environ.get("ASPARE_AUDIT_BUCKET", "")
        if not bucket:
            st.error("Set ASPARE_AUDIT_BUCKET for the S3 audit backend.")
            st.stop()
        prefix = os.environ.get("ASPARE_AUDIT_PREFIX", "audit/")
        return S3AuditRepository(s3_client(), bucket, prefix), f"s3://{bucket}/{prefix}"
    path = Path(os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl"))
    return JsonlAuditRepository(path), str(path)


def _bar_chart(rows: list[dict], x: str, y: str, colors: dict[str, str], sort: list[str] | str | None = None) -> None:
    """Bar chart with an explicit category -> colour mapping (st.bar_chart mis-assigns colours)."""
    chart = (
        alt.Chart(pd.DataFrame(rows))
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X(f"{x}:N", sort=sort, title=None, axis=alt.Axis(labelAngle=-35, labelLimit=120)),
            y=alt.Y(f"{y}:Q", title=None, axis=alt.Axis(tickMinStep=1)),
            color=alt.Color(f"{x}:N", scale=alt.Scale(domain=list(colors), range=list(colors.values())), legend=None),
            tooltip=[x, y],
        )
        .properties(height=240)
    )
    st.altair_chart(chart, width="stretch")


def _badge(kind: str, value: str) -> str:
    css = f"sev-{value}" if kind == "sev" else f"st-{value}"
    return f'<span class="badge {css}">{value}</span>'


def _kicker(text: str, color: str = "#8b9bb4") -> None:
    st.markdown(f'<p class="hero-kicker" style="color: {color}">{text}</p>', unsafe_allow_html=True)


def _badge_text_color(hue_hex: str) -> str:
    """Return dark or light text for a badge sitting on the given hue."""
    h = hue_hex.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#0f172a" if luminance > 0.55 else "#f1f5f9"


def _approval_controls(session: LiveSession, row: FindingRow) -> None:
    """Human-in-the-loop approval for one finding (live mode only)."""
    finding = next((f for f in session.findings if f.finding_id == row.finding_id), None)
    if finding is None or row.status == "REMEDIATED":
        return
    allowed, reason = approval_gate(session, finding)
    mode_label = "dry-run" if session.runtime.settings.dry_run else "applies to AWS"
    if st.button(
        f"Approve fix ({mode_label})",
        key=f"approve-{row.finding_id}",
        disabled=not allowed,
        help=reason or "Runs the remediation, re-inspects the bucket, and records the approval in the audit trail.",
    ):
        with st.spinner("Applying fix and verifying…"):
            outcome = approve(session, finding)
        st.session_state.step = "detected" if outcome is None else "remediated"
        if outcome is None:
            st.toast(f"Dry-run: would run {finding.remediation_action} on {row.resource}")
        elif outcome.verification.verified:
            st.toast(f"Verified: {row.resource} / {row.rule}")
        else:
            st.toast(f"Not verified: {outcome.action_result.message}")
        st.rerun()
    if not allowed:
        st.caption(f"🔒 {reason}")


def render_issue(row: FindingRow) -> None:
    expl = explainer_for(row.rule)
    remediated = row.status == "REMEDIATED"
    if remediated:
        fix_title = "What ASPARe did"
        fix_body = (
            f"<b>{expl['remedy_name']}</b> via <code>{row.remediation}</code>. "
            + (f"{getattr(row, 'remedy_message', '')}. " if getattr(row, "remedy_message", "") else "")
            + f"Verification: <b>{row.verification}</b>."
        )
    elif row.status == "ALERT_AND_LOG":
        fix_title = "What ASPARe will not auto-fix"
        fix_body = expl["remedy_does"]
    else:
        fix_title = "What ASPARe will do"
        fix_body = expl["remedy_does"]

    before = " · ".join(posture_lines(row.before_state)) or "Snapshot captured at detection."
    after = " · ".join(posture_lines(row.after_state)) if row.after_state else ""

    st.markdown(
        f"""
        <div class="issue-card">
          <div>{_badge("sev", row.severity)} {_badge("st", row.status)}
          &nbsp; <code>{row.resource}</code> · {expl["title"]}</div>
          <div class="how-grid">
            <div class="how-box how-what">
              <h4>What is wrong</h4>
              <p>{expl["what"]}</p>
              <p class="muted">{expl["how"]}</p>
            </div>
            <div class="how-box how-hurt">
              <h4>How it affects you</h4>
              <p>{expl["affects"]}</p>
              <p class="muted">{expl["blast_radius"]}</p>
            </div>
            <div class="how-box how-fix">
              <h4>{fix_title}</h4>
              <p>{fix_body}</p>
              <p class="muted">{expl["remedy_leaves"]}</p>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if remediated:
        b1, b2 = st.columns(2)
        with b1:
            st.markdown(
                '<div class="chip-box"><span class="badge st-PENDING">Before</span></div>', unsafe_allow_html=True
            )
            st.caption(before)
        with b2:
            st.markdown(
                '<div class="chip-box"><span class="badge st-COMPLETE">After</span></div>', unsafe_allow_html=True
            )
            st.caption(after or "Re-read after the write.")
    st.caption(" · ".join(expl.get("standards") or []) + f"  ·  detected {row.detected_at}")


with st.sidebar:
    st.markdown(
        f'<p class="hero-kicker">{"Live estate" if live_mode else "Recorded estate"}</p>', unsafe_allow_html=True
    )
    st.subheader(f"{len(buckets)} S3 buckets")
    st.caption(inventory.get("source", ""))
    if not live_mode:
        st.metric("CloudTrail events", len(events))
    classes = sorted({(item.get("tags") or {}).get("DataClass", "?") for item in buckets})
    st.caption("Data classes: " + ", ".join(classes))
    with st.expander("Bucket list"):
        for item in buckets:
            st.caption(f"`{item['name']}` · {(item.get('tags') or {}).get('Purpose')}")

# Backend summary (read-only) drives every dashboard section.
repo, source = _audit_repo()
records = repo.list_records()
snapshot = ReportingAggregator().summarize(records)

severity_dist = ReportingAggregator.severity_distribution(snapshot)
remediation_outcome = ReportingAggregator.remediation_outcome(snapshot)
breakdown = ReportingAggregator.data_class_breakdown(inventory, snapshot)
impact_summary = ReportingAggregator.human_impact_summary(breakdown)
has_records = bool(snapshot.activity)

_kicker("ASPARe · Automated Security Posture Assessment &amp; Remediation")
st.title("Cloud storage security, explained")
st.write(
    "Each finding answers three questions: **what is wrong**, **how that hurts**, and **what the remedy does**. "
    + (
        "**Live mode** scans your real AWS account read-only. Nothing changes until you approve a fix."
        if live_mode
        else "The lab replays a recorded CloudTrail / S3 estate against a mocked S3. It does not call a live AWS account."
    )
)

# 1.4 Helping-people narrative strip — frames the human stakes.
narrative = (
    impact_summary.one_line_narrative or f"No sensitive-class buckets detected across {len(buckets)} estate buckets."
)
st.markdown(
    f"""
    <div class="human-strip">
      <span class="strip-label">What's being protected</span>
      <span class="strip-body">{narrative}</span>
      <span class="strip-cta">View data inventory &rarr;</span>
    </div>
    """,
    unsafe_allow_html=True,
)


def _clear_audit(path: Path) -> None:
    if path.exists():
        path.write_text("")


if live_mode:
    with st.expander("AWS connection", expanded=live is None):
        r1, r2, r3 = st.columns([1, 1, 2])
        region = r1.text_input("Region", os.environ.get("ASPARE_REGION", "us-east-1"))
        profile = r2.text_input("AWS profile (optional)", os.environ.get("AWS_PROFILE", ""))
        dry_run = r3.toggle(
            "Dry-run (approvals are simulated, nothing is written)",
            value=True,
            help="Applied when you press Connect. Turn off to let approved fixes modify real buckets; the safety gate still applies.",
        )
        st.caption(
            "Remediation is limited to buckets in `ASPARE_ALLOWED_BUCKETS` that carry the tag `ASPAReDemo=true`. "
            "Scanning is always read-only."
        )
    b1, b2, b3 = st.columns(3)
    do_connect = b1.button("1. Connect to AWS", width="stretch")
    do_scan = b2.button("2. Scan account (read-only)", width="stretch", disabled=live is None)
    reset = b3.button("Reset session", width="stretch")
    if do_connect:
        try:
            with st.spinner("Validating credentials with STS…"):
                st.session_state.live = connect(region.strip() or "us-east-1", profile.strip() or None, dry_run)
            st.session_state.step = "loaded"
        except LiveConnectionError as exc:
            st.session_state.live = None
            st.error(str(exc))
        else:
            st.rerun()
    if do_scan and live:
        with st.spinner("Inspecting every bucket (read-only)…"):
            _clear_audit(Path(live.audit_path))
            st.session_state.findings = scan(live)
            st.session_state.step = "detected"
        st.rerun()
    if reset:
        if live:
            _clear_audit(Path(live.audit_path))
        st.session_state.live = None
        st.session_state.findings = []
        st.session_state.step = "idle"
        st.rerun()
    step = st.session_state.step
    if step == "idle":
        st.info("Connect with your AWS credentials, scan the account, then approve fixes one by one.")
    elif step == "loaded" and live:
        who = live.identity
        st.info(f"Connected to account **{who['account']}** as `{who['arn']}`. Run a scan next.")
    elif step == "detected":
        st.warning(f"{len(st.session_state.findings)} findings. Open **Issues** to review and approve each fix.")
    elif step == "remediated":
        st.success("Approved fixes finished. Each one was re-inspected — a Put* response alone is not success.")
else:
    b1, b2, b3, b4 = st.columns(4)
    load = b1.button("1. Load estate", width="stretch")
    scan_btn = b2.button("2. Detect findings", width="stretch", disabled=st.session_state.lab is None)
    fix = b3.button("3. Apply auto-remedies", width="stretch", disabled=not st.session_state.findings)
    reset = b4.button("Reset lab", width="stretch")

    if load:
        with st.spinner("Seeding the recorded 40-bucket estate…"):
            stop_lab(st.session_state.lab)
            st.session_state.lab = start_lab()
            st.session_state.findings = []
            st.session_state.step = "loaded"
        st.rerun()

    if scan_btn:
        with st.spinner("Inspecting every recorded bucket and classifying risk…"):
            st.session_state.findings = detect(st.session_state.lab)
            st.session_state.step = "detected"
        st.rerun()

    if fix:
        with st.spinner("Applying auto-approved remediations and re-verifying…"):
            remediate(st.session_state.lab, st.session_state.findings)
            st.session_state.step = "remediated"
        st.rerun()

    if reset:
        stop_lab(st.session_state.lab)
        st.session_state.lab = None
        st.session_state.findings = []
        st.session_state.step = "idle"
        _clear_audit(Path(os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl")))
        st.rerun()

    step = st.session_state.step
    if step == "idle":
        st.info("Load the recorded estate, detect, then apply auto-remedies. Versioning stays alert-only.")
    elif step == "loaded":
        st.info(f"Lab is ready: {len(buckets)} buckets and {len(events)} CloudTrail events are seeded.")
    elif step == "detected":
        pending = sum(1 for item in st.session_state.findings if item.decision is RiskDecision.AUTO_REMEDIATE)
        alerts = sum(1 for item in st.session_state.findings if item.decision is not RiskDecision.AUTO_REMEDIATE)
        st.warning(f"{pending} findings will auto-remediate. {alerts} stay on alert (mostly versioning).")
    elif step == "remediated":
        st.success("Auto-approved writes finished. Each one was re-inspected — a Put* response alone is not success.")

# 2. Metrics cards
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Buckets in estate", len(buckets), delta_color="off")
m2.metric("Findings", snapshot.total_findings, delta_color="inverse" if snapshot.total_findings else "off")
m3.metric("Critical", snapshot.critical_findings, delta_color="inverse" if snapshot.critical_findings else "off")
m4.metric("High", snapshot.high_findings, delta_color="inverse" if snapshot.high_findings else "off")
m5.metric(
    "Remedies verified",
    snapshot.successful_remediations,
    delta_color="normal" if snapshot.successful_remediations else "off",
)
m6.metric(
    "Failed remedies", snapshot.failed_remediations, delta_color="inverse" if snapshot.failed_remediations else "off"
)
st.caption(f"Audit: `{source}` · {len(records)} records · {snapshot.resources_scanned} resources touched this run")

# 3. Charts
c1, c2, c3 = st.columns(3)

with c1:
    st.caption("Findings by severity")
    sev_colors = {"CRITICAL": "#f87171", "HIGH": "#fb923c", "MEDIUM": "#f59e0b", "LOW": "#94a3b8"}
    sev_counts = {
        "CRITICAL": severity_dist.critical,
        "HIGH": severity_dist.high,
        "MEDIUM": severity_dist.medium,
        "LOW": severity_dist.low,
    }
    if any(sev_counts.values()):
        _bar_chart(
            [{"severity": k, "count": v} for k, v in sev_counts.items()],
            "severity",
            "count",
            sev_colors,
            list(sev_colors),
        )
    st.caption(f"{severity_dist.total} findings total — {severity_dist.critical} critical, {severity_dist.high} high.")

with c2:
    st.caption("Remediation outcome")
    if remediation_outcome.total:
        _bar_chart(
            [
                {"outcome": "Verified", "count": remediation_outcome.successful},
                {"outcome": "Failed", "count": remediation_outcome.failed},
            ],
            "outcome",
            "count",
            {"Verified": "#34d399", "Failed": "#f87171"},
            ["Verified", "Failed"],
        )
    st.metric(
        "Verified rate",
        f"{remediation_outcome.success_rate_pct}%",
        delta_color="normal" if remediation_outcome.success_rate_pct else "off",
    )

with c3:
    st.caption("Buckets by data class")
    rows = [{"data_class": b.data_class, "bucket_count": b.bucket_count} for b in breakdown.classes]
    if rows:
        _bar_chart(
            rows,
            "data_class",
            "bucket_count",
            {b.data_class: b.hue_hex for b in breakdown.classes},
            "-y",
        )
    if breakdown.classes:
        top = breakdown.classes[0]
        st.caption(f"Top class: {top.data_class} ({top.bucket_count} buckets)")

# 4. Human impact section
st.divider()
_kicker("Human impact", "#22d3ee")
st.subheader("What's being protected across the estate")
st.write(
    "Each bucket carries a DataClass tag. ASPARe shows how many buckets of each sensitive class are in the estate, "
    "and what the human impact would be if that data were exposed.",
)

cards = impact_summary.protected_classes
if cards:
    cols = st.columns(len(cards))
    for card, col in zip(cards, cols, strict=True):
        with col:
            badge_fg = _badge_text_color(card.hue_hex)
            st.markdown(
                f"""
                <div class="impact-card">
                  <span class="impact-accent" style="background:{card.hue_hex}"></span>
                  <span class="badge" style="background:{card.hue_hex}; color:{badge_fg}">{card.data_class}</span>
                  <div style="font-size: 1.75rem; font-weight: 700; margin: 0.4rem 0 0.1rem 0;">{card.bucket_count}</div>
                  <div style="font-size: 0.72rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: #94a3b8; margin-bottom: 0.5rem;">buckets</div>
                  <p style="margin: 0; font-size: 0.85rem; line-height: 1.45;">{card.impact_statement}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
else:
    st.info("No sensitive-class buckets in the estate.")

if breakdown.total_sensitive_buckets:
    st.caption(
        f"{breakdown.total_protected_sensitive} of {breakdown.total_sensitive_buckets} "
        "sensitive-class buckets have all critical controls (public access block, encryption) in place."
    )

# 7. Pipeline flow — persistent section above the tabs
st.divider()
_kicker("Pipeline", "#22d3ee")
stages = ReportingAggregator.pipeline_state(st.session_state.step, has_records)
cols = st.columns(5)
for stage, col in zip(stages, cols, strict=True):
    with col:
        st.markdown(
            f"""
            <div class="pipeline-step">
              <span class="badge" style="background:#22d3ee; color:#0f172a">{stage.order}</span>
              <div style="font-weight: 600; font-size: 0.85rem; margin: 0.25rem 0 0.1rem 0;">{stage.label}</div>
              <div style="font-size: 0.78rem; color: #94a3b8;">{stage.description}</div>
              <span class="badge st-{stage.status.upper()}">{stage.status.title()}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if stage.order < 5:
            st.markdown('<div class="pipeline-connector">&rarr;</div>', unsafe_allow_html=True)

progress_value = {"idle": 0.0, "loaded": 0.25, "detected": 0.5}.get(step, 0.0)
if step == "remediated":
    progress_value = 1.0 if has_records else 0.75
st.progress(progress_value)

# 5, 6, 8. Tabs
issues, estate, remedies = st.tabs(["Issues — What / How / Remedy", "Estate", "Remedy log"])

with issues:
    if snapshot.total_findings == 0:
        st.info("No findings yet. Click **Load estate**, then **Detect findings**.")
    else:
        severities = sorted({row.severity for row in snapshot.findings if row.severity})
        statuses = sorted({row.status for row in snapshot.findings if row.status})
        rules = sorted({row.rule for row in snapshot.findings if row.rule})
        f1, f2, f3 = st.columns(3)
        selected_sev = f1.multiselect("Severity", severities, default=severities)
        selected_status = f2.multiselect("Status", statuses, default=statuses)
        selected_rules = f3.multiselect("Control", rules, default=rules)
        visible = [
            row
            for row in snapshot.findings
            if (not selected_sev or row.severity in selected_sev)
            and (not selected_status or row.status in selected_status)
            and (not selected_rules or row.rule in selected_rules)
        ]
        st.caption(f"Showing {len(visible)} of {len(snapshot.findings)} findings")
        grouped: dict[str, list[FindingRow]] = defaultdict(list)
        for row in visible:
            grouped[row.resource].append(row)
        first = True
        for resource, rows in grouped.items():
            worst = next((item.severity for item in rows if item.severity == "CRITICAL"), rows[0].severity)
            data_class = ReportingAggregator.data_class_for_resource(resource, inventory) or ""
            with st.expander(f"{resource}  ·  {len(rows)} issue(s)  ·  worst {worst}  ·  {data_class}", expanded=first):
                for row in rows:
                    render_issue(row)
                    if live:
                        _approval_controls(live, row)
                    st.divider()
            first = False

with estate:
    st.write("Every bucket below came from the recorded inventory. Open a row in **Issues** to see why it failed.")
    group_by = st.selectbox("Group by", ["None", "Data Class", "Environment", "Purpose"], index=0)
    by_resource: dict[str, list[FindingRow]] = defaultdict(list)
    for row in snapshot.findings:
        by_resource[row.resource].append(row)
    table = []
    for item in buckets:
        name = item["name"]
        tags = item.get("tags") or {}
        related = by_resource.get(name, [])
        data_class = ReportingAggregator.data_class_for_resource(name, inventory) or tags.get("DataClass", "")
        table.append(
            {
                "Bucket": name,
                "Data class": data_class,
                "Purpose": tags.get("Purpose", ""),
                "Env": tags.get("Environment", ""),
                "Findings": len(related),
                "Critical": sum(1 for row in related if row.severity == "CRITICAL"),
                "Fixed": sum(1 for row in related if row.status == "REMEDIATED"),
                "Alerts": sum(1 for row in related if row.status == "ALERT_AND_LOG"),
            }
        )
    if group_by == "None":
        st.dataframe(table, width="stretch", hide_index=True)
    else:
        grouped_rows: dict[str, list[dict]] = defaultdict(list)
        for row in table:
            grouped_rows[row[group_by]].append(row)
        for name, group_rows in grouped_rows.items():
            entry = HUMAN_IMPACT_MAP.get(name)
            dot = f'<span class="impact-accent" style="background:{entry.hue_hex}"></span>' if entry else ""
            st.markdown(f"### {dot} {name} &middot; {len(group_rows)} buckets", unsafe_allow_html=True)
            st.dataframe(
                [{k: v for k, v in row.items() if k != group_by} for row in group_rows],
                width="stretch",
                hide_index=True,
            )

with remedies:
    if not snapshot.activity:
        st.info("No remediations yet. After detection, click **Apply auto-remedies**.")
    for row in snapshot.activity:
        expl = explainer_for(row.issue)
        result_badge = (
            '<span class="badge st-VERIFIED">Verified</span>'
            if row.verified == "yes"
            else '<span class="badge st-FAILED">Failed</span>'
        )
        with st.expander(
            f"{row.resource} &middot; {expl['remedy_name']} &middot; {row.result} {result_badge}", expanded=False
        ):
            st.markdown(f"**Action:** `{row.action}`")
            st.write(row.message or expl["remedy_does"])
            st.write(expl["remedy_leaves"])
            c1, c2 = st.columns(2)
            c1.markdown("**Before**")
            c1.write("\n".join(f"- {line}" for line in posture_lines(row.before_state)) or "n/a")
            c2.markdown("**After**")
            c2.write("\n".join(f"- {line}" for line in posture_lines(row.after_state)) or "n/a")
            st.caption(f"Verified: {row.verified} &middot; {row.timestamp}")
