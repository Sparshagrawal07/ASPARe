"""Colourful, real-time terminal walkthrough of ASPARe.

Connects to an AWS account (or a built-in simulated estate), then streams each stage of the real engine:
connect, inventory, detect, decide, explain, remediate, verify, audit.

    python -m aspare.terminal --mode demo --fix --yes     # no AWS account needed
    python -m aspare.terminal --mode aws                  # read-only scan of your account
    python -m aspare.terminal --mode aws --seed --fix     # creates and fixes a throwaway bucket (--cleanup deletes it)

Writes only happen with ``--fix``, on buckets that pass the safety gate (tagged ``ASPAReDemo=true``, and listed in
``--allow`` when given), and each one is confirmed unless ``--yes`` is passed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import replace
from typing import Any

try:
    from rich import box
    from rich.console import Console, Group
    from rich.panel import Panel
    from rich.prompt import Confirm
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme
except ImportError:  # pragma: no cover
    sys.stderr.write("The terminal UI needs 'rich'. Install it with:  pip install rich\n")
    raise SystemExit(2) from None

from botocore.exceptions import BotoCoreError, ClientError

from aspare.config.settings import Settings
from aspare.core.enums import RiskDecision
from aspare.core.models import Finding, RemediationOutcome
from aspare.intelligence.reasoner import build_reasoner
from aspare.live import LiveConnectionError, LiveSession, approval_gate, approve, connect, scan, settings_for_live
from aspare.reporting.explainers import posture_lines
from aspare.runtime import build_runtime
from aspare.s3.https_policy import secure_transport_statement

THEME = Theme(
    {
        "brand": "bold #8f9bff",
        "ok": "bold green",
        "bad": "bold red",
        "warn": "bold yellow",
        "dim": "grey62",
        "key": "bold cyan",
        "crit": "bold white on red",
        "high": "bold red",
        "med": "bold yellow",
        "low": "bold blue",
    }
)
LOGO = """\
 ▄▀█ █▀ █▀█ ▄▀█ █▀█ █▀▀
 █▀█ ▄█ █▀▀ █▀█ █▀▄ ██▄"""
CONTROLS = (
    ("Public", "S3_PUBLIC_ACCESS"),
    ("ACL", "S3_PUBLIC_ACL_EXPOSURE"),
    ("Encrypt", "S3_ENCRYPTION_DISABLED"),
    ("HTTPS", "S3_HTTPS_ENFORCEMENT_MISSING"),
    ("Version", "S3_VERSIONING_DISABLED"),
)
SHORT = {
    "S3_PUBLIC_ACCESS": "Public access block",
    "S3_PUBLIC_ACL_EXPOSURE": "Public ACL",
    "S3_ENCRYPTION_DISABLED": "No default encryption",
    "S3_HTTPS_ENFORCEMENT_MISSING": "HTTP allowed",
    "S3_VERSIONING_DISABLED": "Versioning off",
}
READ_CALLS = (
    "GetBucketPublicAccessBlock · GetBucketAcl · GetBucketPolicy · GetEncryptionConfiguration · "
    "GetBucketVersioning · GetBucketTagging · GetBucketOwnershipControls"
)


class Ui:
    def __init__(self, console: Console, speed: float) -> None:
        self.c = console
        self.speed = speed

    def pause(self, seconds: float = 0.25) -> None:
        if self.speed > 0:
            time.sleep(seconds * self.speed)

    def stage(self, number: int, title: str, caption: str) -> None:
        self.c.print()
        self.c.rule(f"[brand]{number}  {title}[/]", style="#8f9bff")
        self.c.print(f"[dim]{caption}[/]\n")

    def banner(self, mode: str) -> None:
        body = Group(
            Text(LOGO, style="brand"),
            Text("Automated Security Posture Assessment & Remediation Engine", style="dim"),
            Text(f"mode: {mode}", style="key"),
        )
        self.c.print(Panel(body, box=box.ROUNDED, border_style="#8f9bff", padding=(1, 3), expand=False))


# ------------------------------------------------------------------ estates


def _demo_session(audit_path: str) -> tuple[LiveSession, Any]:
    import boto3
    from moto import mock_aws

    ctx = mock_aws()
    ctx.start()
    client: Any = boto3.client("s3", region_name="us-east-1")
    estate: list[tuple[str, dict[str, str], dict[str, bool]]] = [
        (
            "ferpa-transcripts-prod",
            {"DataClass": "FERPA", "Environment": "prod"},
            {"pab": False, "enc": False, "ver": False, "https": False, "acl": True},
        ),
        (
            "campus-marketing-site",
            {"DataClass": "PUBLIC", "Purpose": "marketing", "Environment": "prod"},
            {"pab": False, "enc": True, "ver": True, "https": True, "acl": True},
        ),
        (
            "ci-build-cache",
            {"Purpose": "ci-cache", "Environment": "dev"},
            {"pab": True, "enc": True, "ver": False, "https": True, "acl": False},
        ),
        (
            "payroll-archive",
            {"DataClass": "FINANCIAL", "Environment": "prod"},
            {"pab": True, "enc": True, "ver": True, "https": True, "acl": False},
        ),
    ]
    for name, tags, cfg in estate:
        client.create_bucket(Bucket=name)
        tagset = [{"Key": "ASPAReDemo", "Value": "true"}] + [{"Key": k, "Value": v} for k, v in tags.items()]
        client.put_bucket_tagging(Bucket=name, Tagging={"TagSet": tagset})
        client.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={k: cfg["pab"] for k in _PAB_KEYS})
        if cfg["enc"]:
            client.put_bucket_encryption(
                Bucket=name,
                ServerSideEncryptionConfiguration={
                    "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
                },
            )
        if cfg["ver"]:
            client.put_bucket_versioning(Bucket=name, VersioningConfiguration={"Status": "Enabled"})
        if cfg["https"]:
            client.put_bucket_policy(
                Bucket=name,
                Policy=json.dumps({"Version": "2012-10-17", "Statement": [secure_transport_statement(name)]}),
            )
        if cfg["acl"]:
            client.put_bucket_acl(Bucket=name, ACL="public-read")
    runtime = build_runtime(settings_for_live("us-east-1", False, audit_path), client=client)
    identity = {"account": "123456789012", "arn": "arn:aws:iam::123456789012:user/aspare-demo"}
    return LiveSession(runtime=runtime, client=client, identity=identity, audit_path=audit_path), ctx


_PAB_KEYS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")


def _seed_bucket(session: LiveSession) -> str:
    """Create one throwaway, deliberately weak bucket in the connected account (tagged so the safety gate allows it)."""
    region = session.runtime.settings.region
    name = f"aspare-cli-{uuid.uuid4().hex[:10]}-{region}"
    if region == "us-east-1":
        session.client.create_bucket(Bucket=name)
    else:
        session.client.create_bucket(Bucket=name, CreateBucketConfiguration={"LocationConstraint": region})
    session.client.put_bucket_tagging(
        Bucket=name,
        Tagging={"TagSet": [{"Key": "ASPAReDemo", "Value": "true"}, {"Key": "Purpose", "Value": "cli-demo"}]},
    )
    session.client.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration={k: False for k in _PAB_KEYS})
    return name


def _delete_bucket(session: LiveSession, name: str) -> None:
    for call in (session.client.delete_bucket_policy,):
        try:
            call(Bucket=name)
        except Exception:  # noqa: BLE001
            pass
    session.client.delete_bucket(Bucket=name)


# ------------------------------------------------------------------ rendering helpers


def _sev_text(severity: str) -> Text:
    style = {"CRITICAL": "crit", "HIGH": "high", "MEDIUM": "med", "LOW": "low"}.get(severity, "dim")
    return Text(f" {severity[:4] if severity != 'MEDIUM' else 'MED'} ", style=style)


def _decision_text(decision: str | None) -> Text:
    style = {"AUTO_REMEDIATE": "ok", "ALERT_AND_LOG": "warn", "LOG_ONLY": "dim", "MANUAL_REVIEW": "warn"}.get(
        decision or "", "dim"
    )
    label = {"AUTO_REMEDIATE": "auto-fix", "ALERT_AND_LOG": "held", "LOG_ONLY": "log only"}.get(
        decision or "", decision or "-"
    )
    return Text(label, style=style)


def _conf_bar(value: float) -> Text:
    filled = round(value * 8)
    style = "ok" if value >= 0.8 else "warn" if value >= 0.6 else "bad"
    return Text("█" * filled + "░" * (8 - filled), style=style) + Text(f" {value:.0%}", style="dim")


def _fusion(finding: Finding) -> dict[str, Any]:
    return finding.metadata.get("fusion") or {}


def _fused_decision(finding: Finding) -> str:
    return str(_fusion(finding).get("adjusted_decision") or (finding.decision.value if finding.decision else ""))


def _tag_line(tags: dict[str, str]) -> str:
    keep = [f"{k}={v}" for k, v in tags.items() if k in ("DataClass", "Environment", "Purpose")]
    return " ".join(keep)


# ------------------------------------------------------------------ stages


def stage_connect(ui: Ui, session: LiveSession, mode: str, fix: bool) -> None:
    ui.stage(1, "Connect", "Validate credentials with STS (GetCallerIdentity). No keys are stored by ASPARe.")
    acct = session.identity.get("account", "?")
    masked = acct[:4] + "…" + acct[-3:] if len(acct) > 8 else acct
    t = Table.grid(padding=(0, 2))
    t.add_row("[dim]account[/]", f"[key]{masked}[/]" + ("  [dim](simulated)[/]" if mode == "demo" else ""))
    t.add_row("[dim]identity[/]", session.identity.get("arn", "?").replace(acct, masked))
    t.add_row("[dim]region[/]", session.runtime.settings.region)
    t.add_row(
        "[dim]access[/]",
        "[warn]read + write (fix enabled, safety gate still applies)[/]" if fix else "[ok]read-only[/]",
    )
    ui.c.print(Panel(t, title="[ok]connected[/]", border_style="green", expand=False, padding=(0, 2)))


def stage_inventory(ui: Ui, session: LiveSession) -> list[str]:
    ui.stage(2, "Inventory", f"Read-only calls on every bucket: [dim]{READ_CALLS}[/]")
    names = session.runtime.inspector.list_resource_ids()
    with ui.c.status("[brand]listing buckets…[/]", spinner="dots"):
        ui.pause(0.4)
    ui.c.print(f"[ok]✔[/] found [key]{len(names)}[/] bucket(s)\n")
    for name in names:
        with ui.c.status(f"[brand]inspecting[/] {name}", spinner="dots12"):
            session.runtime.inspector.inspect(name)
            ui.pause(0.35)
        ui.c.print(f"  [ok]✔[/] {name}")
    return names


def stage_detect(ui: Ui, session: LiveSession, names: list[str]) -> list[Finding]:
    ui.stage(3, "Detect", "Five reviewed rules mapped to CIS AWS Foundations and AWS FSBP controls.")
    with ui.c.status("[brand]running detection rules…[/]", spinner="dots"):
        findings = scan(session)
        ui.pause(0.5)
    by_bucket: dict[str, set[str]] = {}
    for f in findings:
        by_bucket.setdefault(f.resource_id, set()).add(f.rule_id)
    table = Table(box=box.SIMPLE_HEAVY, header_style="dim", pad_edge=False)
    table.add_column("bucket", style="key", no_wrap=True)
    for label, _ in CONTROLS:
        table.add_column(label, justify="center")
    from rich.live import Live

    with Live(table, console=ui.c, refresh_per_second=12, transient=False):
        for name in names:
            cells = [
                Text("✘", style="bad") if rid in by_bucket.get(name, set()) else Text("✔", style="ok")
                for _, rid in CONTROLS
            ]
            table.add_row(name, *cells)
            ui.pause(0.3)
    ui.c.print(
        f"\n[brand]{len(findings)}[/] finding(s) across [brand]{len(by_bucket)}[/] bucket(s)"
        if findings
        else "\n[ok]No misconfigurations found.[/]"
    )
    return findings


def stage_decide(ui: Ui, findings: list[Finding]) -> list[Finding]:
    ui.stage(
        4,
        "Decide",
        "Fusion combines the rule's severity with behaviour and business context. It can lower an auto-fix to a "
        "human alert, never raise one.",
    )
    ordered = sorted(findings, key=lambda f: -float(_fusion(f).get("priority") or 0))
    table = Table(box=box.SIMPLE_HEAVY, header_style="dim", pad_edge=False)
    for col in ("severity", "bucket", "finding", "severity-only", "ASPARe", "confidence", "prio"):
        table.add_column(col, no_wrap=True)
    from rich.live import Live

    with Live(table, console=ui.c, refresh_per_second=12):
        for f in ordered:
            fu = _fusion(f)
            table.add_row(
                _sev_text(f.severity.value),
                Text(f.resource_id, style="key"),
                SHORT.get(f.rule_id, f.title),
                _decision_text(fu.get("original_decision") or (f.decision.value if f.decision else None)),
                _decision_text(_fused_decision(f)),
                _conf_bar(float(fu.get("confidence") or 0)),
                Text(f"{float(fu.get('priority') or 0):.0f}", style="dim"),
            )
            ui.pause(0.25)
    lowered = [
        f
        for f in ordered
        if _fusion(f).get("original_decision") == RiskDecision.AUTO_REMEDIATE.value
        and _fused_decision(f) != RiskDecision.AUTO_REMEDIATE.value
    ]
    for f in lowered:
        reason = next(
            (r for r in _fusion(f).get("reasons", []) if r.startswith("[")), "context says this may be intended"
        )
        ui.c.print(
            f"\n[warn]held[/] {SHORT.get(f.rule_id, f.title)} on [key]{f.resource_id}[/]: "
            f"a severity-only tool would auto-fix this.\n  [dim]{reason}[/]"
        )
    return ordered


def stage_explain(ui: Ui, session: LiveSession, ordered: list[Finding], limit: int) -> None:
    reasoner = build_reasoner()
    ui.stage(
        5,
        "Explain",
        f"Plain-language reasoning for the most urgent findings ({reasoner.__class__.__name__}, advisory only).",
    )
    tags = {b["name"]: b["tags"] for b in session.inventory["buckets"]}
    for f in ordered[:limit]:
        with ui.c.status("[brand]analysing…[/]", spinner="dots"):
            analysis = reasoner.analyze(f, tags.get(f.resource_id))
            ui.pause(0.4)
        t = Table.grid(padding=(0, 1))
        t.add_column(style="dim", width=14)
        t.add_column()
        t.add_row("what is wrong", analysis.root_cause)
        t.add_row("why it matters", analysis.business_impact)
        t.add_row("recommended", f"[ok]{analysis.recommendation}[/]")
        for c in analysis.caveats:
            t.add_row("caveat", f"[warn]{c}[/]")
        ui.c.print(
            Panel(
                t,
                title=f"{SHORT.get(f.rule_id, f.title)} · [key]{f.resource_id}[/]",
                subtitle=f"[dim]{analysis.source}[/]",
                border_style="#8f9bff",
                padding=(0, 1),
            )
        )


def stage_fix(ui: Ui, session: LiveSession, ordered: list[Finding], fix: bool, yes: bool) -> list[RemediationOutcome]:
    ui.stage(
        6,
        "Remediate",
        "Writes only happen behind the safety gate (allow-list + ASPAReDemo=true tag) and, here, only with --fix.",
    )
    plan: list[tuple[Finding, bool, str]] = []
    for f in ordered:
        if _fused_decision(f) != RiskDecision.AUTO_REMEDIATE.value:
            continue
        ok, why = approval_gate(session, f)
        plan.append((f, ok, why))
    if not plan:
        ui.c.print("[dim]Nothing is eligible for automatic remediation.[/]")
        return []
    table = Table(box=box.SIMPLE_HEAVY, header_style="dim", pad_edge=False)
    for col in ("bucket", "action", "safety gate"):
        table.add_column(col)
    for f, ok, _why in plan:
        table.add_row(
            Text(f.resource_id, style="key"),
            f.remediation_action,
            Text("✔ passes", style="ok") if ok else Text("✘ blocked", style="bad"),
        )
    ui.c.print(table)
    for f, ok, why in plan:
        if not ok:
            ui.c.print(f"[bad]blocked[/] {f.resource_id}: [dim]{why}[/]")
    if not fix:
        ui.c.print("\n[ok]Dry run:[/] nothing was changed. Re-run with [key]--fix[/] to apply the allowed actions.")
        return []
    outcomes: list[RemediationOutcome] = []
    for f, ok, _ in plan:
        if not ok:
            continue
        if not yes and not Confirm.ask(
            f"\nApply [key]{f.remediation_action}[/] to [key]{f.resource_id}[/]?", console=ui.c, default=False
        ):
            ui.c.print("[dim]skipped[/]")
            continue
        with ui.c.status(f"[brand]applying[/] {f.remediation_action} → {f.resource_id}", spinner="bouncingBar"):
            outcome = approve(session, f, approver="aspare-terminal")
            ui.pause(0.6)
        if outcome is None:
            continue
        outcomes.append(outcome)
        stage_verify_line(ui, outcome)
    return outcomes


def stage_verify_line(ui: Ui, outcome: RemediationOutcome) -> None:
    v = outcome.verification
    before = posture_lines(v.before_state or outcome.finding.before_state)
    after = posture_lines(v.after_state)
    head = Text("✔ VERIFIED ", style="ok") if v.verified else Text("✘ NOT VERIFIED ", style="bad")
    head += Text(f"{outcome.finding.remediation_action} on {outcome.finding.resource_id}", style="key")
    rows = Table.grid(padding=(0, 2))
    rows.add_column()
    rows.add_column()
    rows.add_row(Text("before", style="dim"), Text("after", style="dim"))
    changed_rows = 0
    for i in range(max(len(before), len(after))):
        b = before[i] if i < len(before) else ""
        a = after[i] if i < len(after) else ""
        if a != b:
            changed_rows += 1
            rows.add_row(Text(b, style="bad"), Text(a, style="ok"))
    if not changed_rows:
        rows.add_row(Text("(no visible change)", style="dim"), Text(""))
    ui.c.print(
        Panel(
            Group(head, Text(v.message, style="dim"), rows),
            border_style="green" if v.verified else "red",
            padding=(0, 1),
        )
    )


def stage_audit(ui: Ui, session: LiveSession, findings: list[Finding], outcomes: list[RemediationOutcome]) -> None:
    ui.stage(7, "Audit", "Every step is an append-only record, so each action can be traced back to a finding.")
    verified = sum(1 for o in outcomes if o.verification.verified)
    held = sum(1 for f in findings if _fused_decision(f) != RiskDecision.AUTO_REMEDIATE.value)
    t = Table.grid(padding=(0, 3))
    t.add_row(Text(str(len(findings)), style="brand"), "findings")
    t.add_row(Text(str(len(outcomes)), style="brand"), "fixes applied")
    t.add_row(Text(str(verified), style="ok"), "verified by re-reading the cloud")
    t.add_row(Text(str(held), style="warn"), "held for a human or logged only")
    ui.c.print(Panel(t, title="[brand]summary[/]", border_style="#8f9bff", expand=False, padding=(0, 2)))
    ui.c.print(f"[dim]audit trail:[/] {session.audit_path}")
    try:
        lines = [json.loads(x) for x in open(session.audit_path, encoding="utf-8").read().splitlines()[-6:]]
        for rec in lines:
            style = "ok" if rec.get("result") in ("VERIFIED", "SUCCESS") else "dim"
            ui.c.print(
                f"  [dim]{str(rec.get('timestamp', ''))[11:23]}[/] {rec.get('action', ''):<24} "
                f"[{style}]{rec.get('result', '')}[/]"
            )
    except OSError:
        pass


# ------------------------------------------------------------------ entry point


def main(argv: list[str] | None = None, console: Console | None = None) -> int:
    import logging

    logging.disable(logging.INFO)  # keep the engine's JSON logs out of the picture
    p = argparse.ArgumentParser(prog="aspare-terminal", description="Real-time ASPARe walkthrough")
    p.add_argument(
        "--mode", choices=("demo", "aws"), default="demo", help="demo = simulated estate, aws = your account"
    )
    p.add_argument("--region", default=None, help="AWS region (default: ASPARE_REGION / AWS_REGION / us-east-1)")
    p.add_argument("--profile", default=None, help="AWS profile name")
    p.add_argument("--allow", default="", help="comma-separated buckets ASPARe may modify (still needs the tag)")
    p.add_argument("--fix", action="store_true", help="apply allowed automatic fixes (default: read-only)")
    p.add_argument("--yes", action="store_true", help="do not ask before each fix")
    p.add_argument("--seed", action="store_true", help="aws mode: create one throwaway weak bucket to fix")
    p.add_argument("--cleanup", action="store_true", help="aws mode: delete the --seed bucket at the end")
    p.add_argument("--explain", type=int, default=3, help="how many findings to explain")
    p.add_argument("--speed", type=float, default=1.0, help="animation speed factor (0 = no delays)")
    args = p.parse_args(argv)

    ui = Ui(console or Console(theme=THEME), args.speed)
    ui.banner(args.mode if args.mode == "demo" else f"aws ({'fix enabled' if args.fix else 'read-only'})")
    region = args.region or Settings.from_env().region
    ctx = None
    seeded: str | None = None
    try:
        if args.mode == "demo":
            session, ctx = _demo_session("var/audit/terminal-demo.jsonl")
        else:
            try:
                session = connect(region=region, profile=args.profile, dry_run=not args.fix)
            except (LiveConnectionError, BotoCoreError, ClientError) as exc:
                ui.c.print(Panel(str(exc), title="[bad]cannot connect[/]", border_style="red"))
                return 1
            if args.allow:
                allowed = frozenset(x.strip() for x in args.allow.split(",") if x.strip())
                settings = replace(session.runtime.settings, allowed_buckets=allowed)
                session.runtime = build_runtime(settings, client=session.client)
        stage_connect(ui, session, args.mode, args.fix)
        if args.mode == "aws" and args.seed:
            seeded = _seed_bucket(session)
            ui.c.print(f"\n[warn]created throwaway bucket[/] [key]{seeded}[/] (tagged ASPAReDemo=true)")
        names = stage_inventory(ui, session)
        findings = stage_detect(ui, session, names)
        ordered = stage_decide(ui, findings) if findings else []
        if ordered:
            stage_explain(ui, session, ordered, args.explain)
        outcomes = stage_fix(ui, session, ordered, args.fix, args.yes) if ordered else []
        stage_audit(ui, session, findings, outcomes)
        return 0
    finally:
        if seeded and args.cleanup:
            try:
                _delete_bucket(session, seeded)
                ui.c.print(f"[dim]deleted throwaway bucket {seeded}[/]")
            except Exception as exc:  # noqa: BLE001
                ui.c.print(f"[warn]could not delete {seeded}: {exc}[/]")
        elif seeded:
            ui.c.print(
                f"[dim]throwaway bucket left in place: {seeded} (delete it in the S3 console, or use --cleanup)[/]"
            )
        if ctx is not None:
            ctx.stop()


if __name__ == "__main__":
    raise SystemExit(main())
