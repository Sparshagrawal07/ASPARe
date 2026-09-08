"""Remediation Lambda entrypoint."""

from aspare.handlers.detection import remediation_handler

lambda_handler = remediation_handler
