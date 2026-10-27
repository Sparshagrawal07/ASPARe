"""ASPARe Live Showcase — break a real bucket on purpose and watch ASPARe fix it, with reasoning."""

from __future__ import annotations

import html
import os
import re
import time
from typing import Any

import boto3
import streamlit as st

from aspare.live import LiveConnectionError, LiveSession, connect
from aspare.showcase import (
    SCENARIOS,
    ShowcaseEvent,
    ShowcaseState,
    approve_pending,
    cleanup_bucket,
    list_showcase_buckets,
    pending_findings,
    run_scenario,
)

st.set_page_config(page_title="ASPARe · Live Showcase", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
    <style>
      .block-container { max-width: 1250px; padding-top: 1.2rem; }
      .kicker { letter-spacing: .14em; text-transform: uppercase; font-size: .75rem; color: #22d3ee; margin: 0; }
      .scn { border: 1px solid #334155; border-radius: 14px; padding: .9rem 1rem; background: rgba(30,41,59,.55); height: 100%; }
      .scn.sel { border-color: #22d3ee; box-shadow: 0 0 0 1px #22d3ee inset; background: rgba(8,47,73,.55); }
      .scn h4 { margin: 0 0 .25rem 0; font-size: .98rem; }
      .scn p { margin: 0; color: #94a3b8; font-size: .85rem; line-height: 1.4; }
      .stages { display: flex; gap: .5rem; flex-wrap: wrap; margin: .6rem 0 1rem 0; }
      .stage { flex: 1 1 130px; border-radius: 12px; padding: .6rem .8rem; border: 1px solid #334155; background: rgba(15,23,42,.6); }
      .stage b { display: block; font-size: .72rem; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; }
      .stage span { font-size: .85rem; }
      .stage.done { border-color: #10b981; background: rgba(16,185,129,.1); } .stage.done b { color: #34d399; }
      .stage.now { border-color: #22d3ee; background: rgba(34,211,238,.1); } .stage.now b { color: #22d3ee; }
      .stage.bad { border-color: #f87171; background: rgba(248,113,113,.1); } .stage.bad b { color: #f87171; }
      .ev { border-left: 4px solid #475569; border-radius: 10px; padding: .75rem 1rem; margin: .55rem 0; background: rgba(15,23,42,.6); }
      .ev.ok { border-color: #10b981; } .ev.warn { border-color: #f59e0b; } .ev.fail { border-color: #f87171; } .ev.info { border-color: #38bdf8; }
      .ev .tag { font-size: .68rem; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; }
      .ev .ttl { font-weight: 650; font-size: 1rem; margin: .1rem 0 .25rem 0; }
      .ev .dtl { color: #cbd5e1; font-size: .9rem; line-height: 1.45; }
      .why { margin-top: .5rem; padding: .55rem .75rem; border-radius: 8px; background: rgba(34,211,238,.08); border: 1px solid rgba(34,211,238,.25); font-size: .86rem; }
      .ba { display: grid; grid-template-columns: 1fr 1fr; gap: .6rem; margin-top: .55rem; }
      .ba div { border-radius: 8px; padding: .5rem .7rem; font-size: .84rem; }
      .ba .b { background: rgba(248,113,113,.1); border: 1px solid rgba(248,113,113,.3); }
      .ba .a { background: rgba(16,185,129,.1); border: 1px solid rgba(16,185,129,.3); }
      .ba h5 { margin: 0 0 .2rem 0; font-size: .7rem; letter-spacing: .1em; text-transform: uppercase; }
      code { font-size: .82rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

STAGES = [
    ("provision", "1 · Provision"),
    ("misconfigure", "2 · Break"),
    ("detect", "3 · Detect"),
    ("classify", "4 · Decide"),
    ("remediate", "5 · Fix"),
    ("verify", "6 · Verify"),
    ("audit", "7 · Audit"),
]

ss = st.session_state
ss.setdefault("live", None)
ss.setdefault("showcase_events", [])
ss.setdefault("showcase_state", None)
ss.setdefault("showcase_key", "public-policy")
ss.setdefault("showcase_stage", {})


def _default_region() -> str:
    return os.environ.get("ASPARE_REGION") or boto3.Session().region_name or "us-east-1"


def _esc(text: object) -> str:
    """Escape for HTML, rendering `backticks` as <code>."""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(str(text)))


def stage_tracker(placeholder: Any, stage_status: dict[str, str]) -> None:
    cells = []
    for key, label in STAGES:
        cls = stage_status.get(key, "")
        num, name = label.split(" · ")
        cells.append(f'<div class="stage {cls}"><b>{num}</b><span>{name}</span></div>')
    placeholder.markdown(f'<div class="stages">{"".join(cells)}</div>', unsafe_allow_html=True)


def event_card(ev: ShowcaseEvent) -> str:
    d = ev.data
    body = f'<div class="dtl">{_esc(ev.detail)}</div>' if ev.detail else ""
    if ev.stage == "misconfigure":
        calls = "".join(f"<li><code>{_esc(c)}</code></li>" for c in d.get("api_calls", []))
        body += f"<div class='dtl' style='margin-top:.4rem'>Real AWS calls:<ul style='margin:.2rem 0 0 1.1rem'>{calls}</ul></div>"
    if ev.stage == "detect" and d.get("snapshot"):
        items = " · ".join(_esc(x) for x in d["snapshot"])
        body += f"<div class='dtl' style='margin-top:.4rem'><b>Live snapshot:</b> {items}</div>"
    if ev.stage == "classify":
        body += f'<div class="dtl" style="margin-top:.4rem"><b>Why it matters:</b> {_esc(d.get("why_it_matters", ""))}</div>'
        body += (
            f'<div class="why"><b>Decision: {_esc(d.get("decision"))}</b><br>{_esc(d.get("reasoning", ""))}'
            + (f"<br><i>{_esc(' · '.join(d.get('standards') or []))}</i>" if d.get("standards") else "")
            + "</div>"
        )
    if ev.stage == "verify":
        before = "<br>".join(_esc(x) for x in d.get("before", [])) or "n/a"
        after = "<br>".join(_esc(x) for x in d.get("after", [])) or "n/a"
        body += (
            f'<div class="dtl" style="margin-top:.4rem">Action <code>{_esc(d.get("action"))}</code> on rule '
            f"<code>{_esc(d.get('rule'))}</code></div>"
            f'<div class="ba"><div class="b"><h5>Before</h5>{before}</div><div class="a"><h5>After (re-read from AWS)</h5>{after}</div></div>'
        )
    return f'<div class="ev {ev.status}"><div class="tag">{_esc(ev.stage)}</div><div class="ttl">{_esc(ev.title)}</div>{body}</div>'


def stage_status_from(events: list[ShowcaseEvent], done: bool = True) -> dict[str, str]:
    status: dict[str, str] = {}
    for ev in events:
        status[ev.stage] = "bad" if ev.status == "fail" and ev.stage in {"verify"} else "done"
    if events and not done:
        status[events[-1].stage] = "now"
    return status


# ---------- header ----------
st.markdown('<p class="kicker">ASPARe · Live showcase</p>', unsafe_allow_html=True)
st.title("Watch a cloud misconfiguration fix itself")
st.write(
    "Pick a scenario. ASPARe creates a **throwaway bucket in your real AWS account**, breaks it on purpose, then "
    "detects, reasons about, fixes and verifies the problem live. Only buckets named `aspare-showcase-*` and tagged "
    "`ASPAReDemo=true` are ever touched."
)

# ---------- connection ----------
live: LiveSession | None = ss.live
with st.container(border=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1, 1.4], vertical_alignment="bottom")
    region = c1.text_input("AWS region", _default_region())
    profile = c2.text_input("AWS profile (optional)", os.environ.get("AWS_PROFILE", ""))
    if c3.button("Connect to AWS", width="stretch", type="primary" if live is None else "secondary"):
        try:
            ss.live = connect(region.strip(), profile.strip() or None, dry_run=False)
            st.rerun()
        except LiveConnectionError as exc:
            ss.live = None
            st.error(str(exc))
    if live:
        c4.success(f"Connected · account {live.identity['account']} · {live.runtime.settings.region}")
    else:
        c4.info("Not connected")
if live is None:
    st.stop()

# ---------- scenarios ----------
st.subheader("Choose a scenario")
cols = st.columns(len(SCENARIOS))
for (key, scn), col in zip(SCENARIOS.items(), cols, strict=True):
    with col:
        sel = " sel" if ss.showcase_key == key else ""
        st.markdown(
            f'<div class="scn{sel}"><h4>{_esc(scn.title)}</h4><p>{_esc(scn.tagline)}</p></div>', unsafe_allow_html=True
        )
        if st.button("Select" if ss.showcase_key != key else "Selected ✓", key=f"pick-{key}", width="stretch"):
            ss.showcase_key = key
            st.rerun()

scenario = SCENARIOS[ss.showcase_key]
st.caption(f"**{scenario.title}** — {scenario.story}")

o1, o2, o3 = st.columns([1.3, 1.3, 1])
mode = o1.radio(
    "Remediation mode",
    ["Autonomous (ASPARe decides)", "Human-approved (you click)"],
    help="Autonomous mode fixes CRITICAL/HIGH findings on its own; MEDIUM ones always wait for you.",
)
pace = o2.slider("Presentation pace (seconds per step)", 0.0, 3.0, 1.2, 0.1)
run = o3.button("▶ Run showcase", width="stretch", type="primary")

st.divider()
tracker = st.empty()
timeline = st.container()

if run:
    ss.showcase_events = []
    ss.showcase_state = None
    status: dict[str, str] = {}
    stage_tracker(tracker, status)
    try:
        for item in run_scenario(live, scenario, autonomous=mode.startswith("Autonomous")):
            if isinstance(item, ShowcaseState):
                ss.showcase_state = item
                break
            ss.showcase_events.append(item)
            status = stage_status_from(ss.showcase_events, done=False)
            stage_tracker(tracker, status)
            with timeline:
                st.markdown(event_card(item), unsafe_allow_html=True)
            time.sleep(pace)
    except Exception as exc:  # noqa: BLE001 - show AWS errors to the presenter instead of a stack trace
        st.error(f"The showcase stopped: {exc}")
    stage_tracker(tracker, stage_status_from(ss.showcase_events, done=True))
else:
    stage_tracker(tracker, stage_status_from(ss.showcase_events, done=True))
    with timeline:
        for ev in ss.showcase_events:
            st.markdown(event_card(ev), unsafe_allow_html=True)
        if not ss.showcase_events:
            st.info("Press **Run showcase** to begin.")

# ---------- after the run ----------
state: ShowcaseState | None = ss.showcase_state
if state:
    st.divider()
    held = pending_findings(state)
    if held:
        st.subheader("Waiting for your approval")
        for finding in held:
            a, b = st.columns([4, 1], vertical_alignment="center")
            a.markdown(f"**{finding.severity.value}** · `{finding.rule_id}` · {finding.title}")
            if b.button("Approve fix", key=f"appr-{finding.finding_id}", width="stretch", type="primary"):
                with st.spinner("Applying and verifying…"):
                    ss.showcase_events.append(approve_pending(live, state, finding, "showcase-presenter"))
                st.rerun()
    else:
        st.success("Nothing left waiting: every fixable finding is verified.")

    st.subheader("Prove it in AWS")
    region_name = live.runtime.settings.region
    st.code(
        f"aws s3api get-public-access-block --bucket {state.bucket} --region {region_name}\n"
        f"aws s3api get-bucket-policy --bucket {state.bucket} --region {region_name}",
        language="bash",
    )
    st.link_button(
        "Open the bucket in the AWS console",
        f"https://s3.console.aws.amazon.com/s3/buckets/{state.bucket}?region={region_name}&tab=permissions",
    )

# ---------- housekeeping ----------
with st.expander("Clean up showcase buckets"):
    buckets = list_showcase_buckets(live)
    if not buckets:
        st.caption("No showcase buckets exist.")
    for name in buckets:
        x, y = st.columns([4, 1], vertical_alignment="center")
        x.code(name, language=None)
        if y.button("Delete", key=f"del-{name}", width="stretch"):
            cleanup_bucket(live, name)
            if state and state.bucket == name:
                ss.showcase_state = None
            st.rerun()
