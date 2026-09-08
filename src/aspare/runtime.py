"""Dependency construction for CLI, tests, and Lambda handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aspare.audit.repository import (
    FallbackAuditRepository,
    JsonlAuditRepository,
    MemoryAuditRepository,
    S3AuditRepository,
)
from aspare.config.settings import Settings
from aspare.core.interfaces import AuditRepository, FindingPublisher
from aspare.detection.engine import DetectionEngine
from aspare.detection.rules.s3 import default_s3_rules
from aspare.events.normalizer import EventNormalizer
from aspare.inventory.service import InventoryService
from aspare.policy.registry import PolicyRegistry
from aspare.providers.aws import AwsS3Provider
from aspare.providers.aws.client import s3_client
from aspare.providers.aws.s3_inspector import S3Inspector
from aspare.providers.aws.s3_remediator import S3Remediator
from aspare.providers.registry import ProviderRegistry
from aspare.remediation.actions.s3 import default_s3_actions
from aspare.remediation.engine import RemediationEngine
from aspare.remediation.safety import SafetyGate
from aspare.risk.evaluator import RiskEvaluator, RiskPolicy
from aspare.verification.engine import VerificationEngine
from aspare.workflows.detection import DetectionWorkflow
from aspare.workflows.pipeline import Pipeline
from aspare.workflows.publishers import EventBridgePublisher, InProcessPublisher
from aspare.workflows.remediation import RemediationWorkflow


@dataclass
class Runtime:
    settings: Settings
    policy: PolicyRegistry
    audit: AuditRepository
    publisher: FindingPublisher
    detection_workflow: DetectionWorkflow
    remediation_workflow: RemediationWorkflow
    pipeline: Pipeline
    inspector: S3Inspector
    remediator: S3Remediator


def build_audit(settings: Settings, client: Any | None = None) -> AuditRepository:
    if settings.audit_backend == "memory":
        primary: AuditRepository = MemoryAuditRepository()
    elif settings.audit_backend == "s3":
        if not settings.audit_bucket:
            raise ValueError("ASPARE_AUDIT_BUCKET is required for the s3 audit backend")
        primary = S3AuditRepository(
            client or s3_client(settings.region), settings.audit_bucket, settings.audit_prefix
        )
    else:
        primary = JsonlAuditRepository(settings.audit_path)
    return FallbackAuditRepository(primary)


def build_runtime(
    settings: Settings | None = None,
    client: Any | None = None,
    publisher: FindingPublisher | None = None,
    events_client: Any | None = None,
) -> Runtime:
    settings = settings or Settings.from_env()
    s3 = client or s3_client(settings.region)
    inspector = S3Inspector(s3, settings.region)
    remediator = S3Remediator(s3, settings.region)
    providers = ProviderRegistry()
    providers.register(AwsS3Provider(inspector, remediator))
    policy = PolicyRegistry.from_path(settings.policy_path)
    detection = DetectionEngine(default_s3_rules(policy, settings))
    risk = RiskEvaluator(RiskPolicy.from_path(settings.risk_policy_path))
    audit = build_audit(settings, s3)
    in_process = publisher if isinstance(publisher, InProcessPublisher) else InProcessPublisher()
    if publisher is None:
        if settings.event_bus_name:
            import boto3

            events = events_client or boto3.client("events", region_name=settings.region)
            publisher = EventBridgePublisher(events, settings.event_bus_name)
        else:
            publisher = in_process
    inventory = InventoryService(providers, settings)
    detection_workflow = DetectionWorkflow(
        EventNormalizer(), inventory, detection, risk, audit, publisher
    )
    remediation_workflow = RemediationWorkflow(
        RemediationEngine(default_s3_actions(remediator, settings, SafetyGate(settings))),
        VerificationEngine(inspector, detection),
        audit,
    )
    pipeline_publisher = in_process if isinstance(publisher, InProcessPublisher) else InProcessPublisher()
    if isinstance(publisher, InProcessPublisher):
        pipeline = Pipeline(detection_workflow, remediation_workflow, publisher)
    else:
        pipeline = Pipeline(
            DetectionWorkflow(EventNormalizer(), inventory, detection, risk, audit, pipeline_publisher),
            remediation_workflow,
            pipeline_publisher,
        )
    return Runtime(
        settings=settings,
        policy=policy,
        audit=audit,
        publisher=publisher,
        detection_workflow=detection_workflow,
        remediation_workflow=remediation_workflow,
        pipeline=pipeline,
        inspector=inspector,
        remediator=remediator,
    )
