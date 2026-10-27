"""ASPARe Intelligence — fused triage, explanations, incidents, least-privilege policies, benchmark, multi-cloud."""

from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from aspare.dataset import detect, start_lab, stop_lab
from aspare.intelligence.benchmark import run as run_benchmark
from aspare.intelligence.fusion import FusionEngine, FusionResult
from aspare.intelligence.reasoner import ClaudeReasoner, OfflineReasoner, build_reasoner
from aspare.multicloud_demo import run_demo
from aspare.policygen import generate_policies, validate_least_privilege

st.set_page_config(page_title="ASPARe · Intelligence", layout="wide", initial_sidebar_state="collapsed")
st.markdown(
    """
    <style>
      .block-container { max-width: 1300px; padding-top: 1.2rem; }
      .kicker { letter-spacing: .14em; text-transform: uppercase; font-size: .75rem; color: #22d3ee; margin: 0; }
      .card { border: 1px solid #334155; border-radius: 14px; padding: .9rem 1.1rem; background: rgba(30,41,59,.55); margin-bottom: .6rem; }
      .card h4 { margin: 0 0 .3rem 0; font-size: .8rem; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; }
      .card p { margin: 0; font-size: .92rem; line-height: 1.5; }
      .chip { display:inline-block; padding:.1rem .55rem; border-radius:999px; font-size:.72rem; font-weight:700; background:#1e293b; margin-right:.3rem; }
      .chip.down { background:#3f2412; color:#fdba74; } .chip.esc { background:#450a0a; color:#fca5a5; }
    </style>
    """,
    unsafe_allow_html=True,
)
ss = st.session_state
ss.setdefault("lab", None)
ss.setdefault("findings", [])
ss.setdefault("analyses", {})

st.markdown('<p class="kicker">ASPARe · Intelligence layer</p>', unsafe_allow_html=True)
st.title("Why ASPARe decided what it decided")
st.write(
    "Rule findings are fused with behavioural evidence from change events and business context into a **confidence** "
    "and **priority**. ASPARe can lower an automatic fix to an alert when the configuration may be intentional, and "
    "never raises one to automatic. Every number below is derived from real evidence and shown with its reasons."
)

if ss.lab is None or not ss.findings:
    st.info("Load and analyse the recorded 42-bucket estate (mocked S3, no AWS calls).")
    if st.button("Load and analyse estate", type="primary"):
        with st.spinner("Seeding, scanning and fusing evidence…"):
            stop_lab(ss.lab)
            ss.lab = start_lab()
            ss.findings = detect(ss.lab)
        st.rerun()

findings = ss.findings
fusions = [FusionResult.from_dict(f.metadata["fusion"]) for f in findings if f.metadata.get("fusion")]
tab_queue, tab_explain, tab_inc, tab_policy, tab_bench, tab_cloud = st.tabs(
    ["Priority queue", "Explain a finding", "Incidents", "Least-privilege policy", "Benchmark", "Multi-cloud"]
)

with tab_queue:
    if not fusions:
        st.caption("Nothing analysed yet.")
    else:
        changed = [r for r in fusions if r.original_decision is not r.adjusted_decision]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Findings", len(fusions))
        c2.metric("Decisions changed by context", len(changed))
        c3.metric("Escalations", sum(1 for r in fusions if r.escalate))
        c4.metric("Avg confidence", f"{sum(r.confidence for r in fusions) / len(fusions):.2f}")
        only_changed = st.toggle("Show only decisions fusion changed", value=False)
        rows = [
            {
                "Priority": round(r.priority, 1),
                "Bucket": r.resource_id,
                "Rule": r.rule_id,
                "Rule-only": r.original_decision.value,
                "Fused": r.adjusted_decision.value,
                "Confidence": round(r.confidence, 2),
                "Anomaly": (r.anomaly or {}).get("score"),
                "Context rules": ", ".join(r.rules_applied),
            }
            for r in sorted(fusions, key=lambda x: -x.priority)
            if not only_changed or r.original_decision is not r.adjusted_decision
        ]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True, height=420)
        st.caption(
            "Priority = severity × confidence × context multipliers + anomaly bonus. Confidence is an evidence-weighted "
            "score, not a calibrated probability."
        )

with tab_explain:
    if not findings:
        st.caption("Nothing analysed yet.")
    else:
        ranked = sorted(
            [f for f in findings if f.metadata.get("fusion")], key=lambda f: -f.metadata["fusion"]["priority"]
        )
        labels = {f"{f.resource_id} · {f.rule_id}": f for f in ranked}
        choice = st.selectbox("Finding (highest priority first)", list(labels))
        finding = labels[choice]
        fusion = finding.metadata["fusion"]
        tags = (finding.before_state or {}).get("tags") or {}
        left, right = st.columns([1.1, 1])
        with left:
            st.markdown("#### Evidence and reasoning")
            for reason in fusion["reasons"]:
                st.markdown(f"- {reason}")
            signals = (fusion.get("anomaly") or {}).get("signals") or []
            if signals:
                st.markdown("**Behavioural signals**")
                st.dataframe(
                    pd.DataFrame(signals).rename(columns={"name": "Signal", "value": "Strength", "explanation": "Why"}),
                    hide_index=True,
                    width="stretch",
                )
            else:
                st.caption("No behavioural evidence for this finding (it came from a scan, not a change event).")
            st.caption(f"Tags: {tags or 'n/a'}")
        with right:
            st.markdown("#### Analysis")
            reasoner = build_reasoner()
            using_claude = isinstance(reasoner, ClaudeReasoner)
            st.caption(
                f"Reasoner: **{'Claude (' + reasoner.model + ')' if using_claude else 'offline (no ANTHROPIC_API_KEY)'}**. "
                "Advisory only: nothing it says is executed."
            )
            if st.button("Analyse this finding"):
                with st.spinner("Reasoning…"):
                    ss.analyses[choice] = reasoner.analyze(finding, tags)
            analysis = ss.analyses.get(choice) or OfflineReasoner().analyze(finding, tags)
            for title, body in (
                ("Summary", analysis.summary),
                ("Root cause", analysis.root_cause),
                ("Business impact", analysis.business_impact),
                ("Recommendation", analysis.recommendation),
            ):
                st.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)
            for note in analysis.caveats:
                st.warning(note)
            st.caption(f"Source: {analysis.source}" + (f" · {analysis.model}" if analysis.model else ""))

with tab_inc:
    if not fusions:
        st.caption("Nothing analysed yet.")
    else:
        incidents = FusionEngine().correlate(fusions)
        if not incidents:
            st.success("No correlated incidents: findings are independent.")
        for inc in incidents:
            st.markdown(
                f'<div class="card"><h4>{inc.kind} · {inc.severity}</h4><p><b>{inc.resource_id}</b> — {inc.summary}'
                f" ({len(inc.finding_ids)} findings)</p></div>",
                unsafe_allow_html=True,
            )

with tab_policy:
    st.write(
        "ASPARe's own roles should hold the smallest permissions that work. Enter the buckets ASPARe may modify; the "
        "generator emits detection and remediation policies and checks them for wildcards. Policies are proposals "
        "for human review."
    )
    names = st.text_input("Buckets (comma-separated)", os.environ.get("ASPARE_ALLOWED_BUCKETS", "aspare-test-bucket"))
    audit_bucket = st.text_input("Audit bucket (optional)", "")
    chosen = [n.strip() for n in names.split(",") if n.strip()]
    if chosen:
        policies = generate_policies(chosen, audit_bucket=audit_bucket or None)
        for role, policy in policies.items():
            problems = validate_least_privilege(policy)
            st.markdown(
                f"**{role.title()} role** — {'✅ least-privilege checks passed' if not problems else '❌ ' + '; '.join(problems)}"
            )
            st.json(policy.document, expanded=False)
            with st.expander("Why each statement exists, and review checklist"):
                for sid, why in policy.rationale.items():
                    st.markdown(f"- `{sid}` — {why}")
                for item in policy.review_checklist:
                    st.markdown(f"- ☐ {item}")

with tab_bench:
    result = run_benchmark()
    st.write(
        f"Synthetic triage benchmark: **{result['cases']} hand-labelled cases**. Labels were written by the project, "
        "not independent annotators, so this is a regression check on handled situations, **not** evidence of real-world accuracy."
    )
    ro, fu = result["rule_only"], result["fused"]
    table = pd.DataFrame(
        {
            "Metric": [
                "Decision accuracy vs label",
                "Unsafe auto-remediations",
                "Missed auto-remediations",
                "Needless alerts",
                f"Precision@{fu['k']} urgent findings",
            ],
            "Rule-only": [
                ro["decision_accuracy"],
                ro["unsafe_auto_remediations"],
                ro["missed_auto_remediations"],
                ro["needless_alerts"],
                ro["precision_at_k_urgent"],
            ],
            "Fused": [
                fu["decision_accuracy"],
                fu["unsafe_auto_remediations"],
                fu["missed_auto_remediations"],
                fu["needless_alerts"],
                fu["precision_at_k_urgent"],
            ],
        }
    )
    st.dataframe(table, hide_index=True, width="stretch")
    with st.expander("Per-case decisions"):
        st.dataframe(pd.DataFrame(result["rows"]), hide_index=True, width="stretch")

with tab_cloud:
    st.write(
        "One pipeline, three clouds. This runs a **simulated** Azure and Google Cloud estate (no accounts needed) through "
        "the same detection, fusion, remediation and verification code that handles AWS."
    )
    if st.button("Run simulated Azure + GCS estate", type="primary"):
        with st.spinner("Scanning Azure and GCS…"):
            ss.multicloud = run_demo()
    demo = ss.get("multicloud")
    if demo:
        df = pd.DataFrame(demo.rows)
        st.dataframe(df, hide_index=True, width="stretch")
        downgraded = df[(df["rule_only"] == "AUTO_REMEDIATE") & (df["fused"] != "AUTO_REMEDIATE")]
        if len(downgraded):
            st.info(
                f"{len(downgraded)} finding(s) would have been auto-fixed by a severity-only policy but were held for a "
                "human: context says the exposure may be intentional (e.g. a public marketing site)."
            )
        st.caption(
            f"Verified fixes: {int((df['result'] == 'VERIFIED').sum())} · "
            f"Failed: {int((df['result'] == 'FAILED').sum())}. Real Azure/GCS use `aspare[azure]` / `aspare[gcp]` credentials."
        )
