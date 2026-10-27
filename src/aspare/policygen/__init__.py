"""Least-privilege IAM policy generation for ASPARe's own roles."""

from aspare.policygen.generator import (
    GeneratedPolicy,
    generate_policies,
    iam_action_for_operation,
    required_actions,
    validate_least_privilege,
)

__all__ = [
    "GeneratedPolicy",
    "generate_policies",
    "iam_action_for_operation",
    "required_actions",
    "validate_least_privilege",
]
