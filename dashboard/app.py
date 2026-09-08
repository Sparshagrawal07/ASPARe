"""ASPARe dashboard — What happened, how it hurts, what the remedy did."""

from __future__ import annotations

import os
from collections import defaultdict
from pathlib import Path

import streamlit as st

from aspare.audit.repository import JsonlAuditRepository, S3AuditRepository
from aspare.core.enums import RiskDecision
from aspare.dataset import detect, load_events, load_inventory, remediate, start_lab, stop_lab
from aspare.providers.aws.client import s3_client
from aspare.reporting.aggregator import FindingRow, ReportingAggregator
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

inventory = load_inventory()
events = load_events()
buckets = inventory.get("buckets") or []


def _audit_repo():
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


def _badge(kind: str, value: str) -> str:
    css = f"sev-{value}" if kind == "sev" else f"st-{value}"
    return f'<span class="badge {css}">{value}</span>'


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
        b1.markdown("**Before**")
        b1.caption(before)
        b2.markdown("**After the remedy**")
        b2.caption(after or "Re-read after the write.")
    st.caption(" · ".join(expl.get("standards") or []) + f"  ·  detected {row.detected_at}")


with st.sidebar:
    st.markdown('<p class="hero-kicker">Recorded estate</p>', unsafe_allow_html=True)
    st.subheader(f"{len(buckets)} S3 buckets")
    st.caption(inventory.get("source", ""))
    st.metric("CloudTrail events", len(events))
    classes = sorted({(item.get("tags") or {}).get("DataClass", "?") for item in buckets})
    st.caption("Data classes: " + ", ".join(classes))
    with st.expander("Bucket list"):
        for item in buckets:
            st.caption(f"`{item['name']}` · {(item.get('tags') or {}).get('Purpose')}")

st.markdown('<p class="hero-kicker">ASPARe</p>', unsafe_allow_html=True)
st.title("Security posture, explained")
st.write(
    "Each finding answers three questions: **what is wrong**, **how that hurts**, and **what the remedy does**. "
    "The lab replays a recorded CloudTrail / S3 estate. It does not call a live AWS account."
)

b1, b2, b3, b4 = st.columns(4)
load = b1.button("1. Load estate", width="stretch")
scan = b2.button("2. Detect findings", width="stretch", disabled=st.session_state.lab is None)
fix = b3.button("3. Apply auto-remedies", width="stretch", disabled=not st.session_state.findings)
reset = b4.button("Reset lab", width="stretch")

if load:
    with st.spinner("Seeding the recorded 40-bucket estate…"):
        stop_lab(st.session_state.lab)
        st.session_state.lab = start_lab()
        st.session_state.findings = []
        st.session_state.step = "loaded"
    st.rerun()

if scan:
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
    path = Path(os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl"))
    if path.exists():
        path.write_text("")
    st.rerun()

step = st.session_state.step
st.progress({"idle": 0.0, "loaded": 0.33, "detected": 0.66, "remediated": 1.0}.get(step, 0.0))
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

repo, source = _audit_repo()
records = repo.list_records()
snapshot = ReportingAggregator().summarize(records)

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Buckets in estate", len(buckets))
m2.metric("Findings", snapshot.total_findings)
m3.metric("Critical", snapshot.critical_findings)
m4.metric("High", snapshot.high_findings)
m5.metric("Remedies verified", snapshot.successful_remediations)
m6.metric("Failed remedies", snapshot.failed_remediations)
st.caption(f"Audit: `{source}` · {len(records)} records · {snapshot.resources_scanned} resources touched this run")

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
            with st.expander(f"{resource}  ·  {len(rows)} issue(s)  ·  worst {worst}", expanded=first):
                for row in rows:
                    render_issue(row)
                    st.divider()
            first = False

with estate:
    st.write("Every bucket below came from the recorded inventory. Open a row in **Issues** to see why it failed.")
    by_resource: dict[str, list[FindingRow]] = defaultdict(list)
    for row in snapshot.findings:
        by_resource[row.resource].append(row)
    table = []
    for item in buckets:
        name = item["name"]
        tags = item.get("tags") or {}
        related = by_resource.get(name, [])
        table.append(
            {
                "Bucket": name,
                "Data class": tags.get("DataClass", ""),
                "Purpose": tags.get("Purpose", ""),
                "Env": tags.get("Environment", ""),
                "Findings": len(related),
                "Critical": sum(1 for row in related if row.severity == "CRITICAL"),
                "Fixed": sum(1 for row in related if row.status == "REMEDIATED"),
                "Alerts": sum(1 for row in related if row.status == "ALERT_AND_LOG"),
            }
        )
    st.dataframe(table, width="stretch", hide_index=True)

with remedies:
    if not snapshot.activity:
        st.info("No remediations yet. After detection, click **Apply auto-remedies**.")
    for row in snapshot.activity:
        expl = explainer_for(row.issue)
        with st.expander(f"{row.resource}  ·  {expl['remedy_name']}  ·  {row.result}", expanded=False):
            st.markdown(f"**Action:** `{row.action}`")
            st.write(row.message or expl["remedy_does"])
            st.write(expl["remedy_leaves"])
            c1, c2 = st.columns(2)
            c1.markdown("**Before**")
            c1.write("\n".join(f"- {line}" for line in posture_lines(row.before_state)) or "n/a")
            c2.markdown("**After**")
            c2.write("\n".join(f"- {line}" for line in posture_lines(row.after_state)) or "n/a")
            st.caption(f"Verified: {row.verified} · {row.timestamp}")
