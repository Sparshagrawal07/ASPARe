"""Application workflows."""

from aspare.workflows.detection import DetectionWorkflow
from aspare.workflows.pipeline import Pipeline, PipelineResult
from aspare.workflows.remediation import RemediationWorkflow

__all__ = ["DetectionWorkflow", "Pipeline", "PipelineResult", "RemediationWorkflow"]
