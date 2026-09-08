"""Detection package."""

from aspare.detection.engine import DetectionEngine
from aspare.detection.rules.s3 import default_s3_rules

__all__ = ["DetectionEngine", "default_s3_rules"]
