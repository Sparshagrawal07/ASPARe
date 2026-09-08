"""ASPARe dashboard — read-only view of audit records."""

from __future__ import annotations

import os
from pathlib import Path

import streamlit as st

from aspare.audit.repository import JsonlAuditRepository, S3AuditRepository
from aspare.providers.aws.client import s3_client
from aspare.reporting.aggregator import ReportingAggregator

st.set_page_config(page_title="ASPARe Dashboard", layout="wide")
st.title("ASPARe")
st.caption("Automated Security Posture Assessment & Remediation Engine")
st.write(
    "Read-only view of deterministic detection, risk decisions, remediation, and verification. "
    "This dashboard does not mutate cloud resources."
)

backend = os.environ.get("ASPARE_AUDIT_BACKEND", "jsonl")
if backend == "s3":
    bucket = os.environ.get("ASPARE_AUDIT_BUCKET", "")
    prefix = os.environ.get("ASPARE_AUDIT_PREFIX", "audit/")
    if not bucket:
        st.error("Set ASPARE_AUDIT_BUCKET for the S3 audit backend.")
        st.stop()
    repo = S3AuditRepository(s3_client(), bucket, prefix)
    source = f"s3://{bucket}/{prefix}"
else:
    path = Path(os.environ.get("ASPARE_AUDIT_PATH", "var/audit/aspare.jsonl"))
    repo = JsonlAuditRepository(path)
    source = str(path)

records = repo.list_records()
snapshot = ReportingAggregator().summarize(records)
st.caption(f"Audit source: `{source}` ({len(records)} records)")

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Resources scanned", snapshot.resources_scanned)
c2.metric("Total findings", snapshot.total_findings)
c3.metric("Critical", snapshot.critical_findings)
c4.metric("High", snapshot.high_findings)
c5.metric("Medium", snapshot.medium_findings)
c6.metric("Remediations OK", snapshot.successful_remediations)
c7.metric("Remediations failed", snapshot.failed_remediations)

st.subheader("Findings")
severities = sorted({row.severity for row in snapshot.findings if row.severity})
statuses = sorted({row.status for row in snapshot.findings if row.status})
fc1, fc2 = st.columns(2)
selected_sev = fc1.multiselect("Severity", severities, default=severities)
selected_status = fc2.multiselect("Status", statuses, default=statuses)
rows = [
    {
        "Resource": row.resource,
        "Rule": row.rule,
        "Severity": row.severity,
        "Status": row.status,
        "Detected At": row.detected_at,
        "Remediation": row.remediation,
        "Verification": row.verification,
    }
    for row in snapshot.findings
    if (not selected_sev or row.severity in selected_sev)
    and (not selected_status or row.status in selected_status)
]
st.dataframe(rows, use_container_width=True, hide_index=True)

st.subheader("Recent remediation activity")
activity = [
    {
        "resource": row.resource,
        "issue": row.issue,
        "action": row.action,
        "result": row.result,
        "verified": row.verified,
        "timestamp": row.timestamp,
    }
    for row in snapshot.activity
]
st.dataframe(activity, use_container_width=True, hide_index=True)

if snapshot.total_findings == 0:
    st.info("No findings yet. Run `python -m aspare.cli --mode mocked` then refresh.")
