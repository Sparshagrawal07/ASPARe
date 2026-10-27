#!/usr/bin/env bash
# Remove the ASPARe stack. The audit bucket is versioned, so empty it first if you want it gone.
set -euo pipefail
REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}
aws cloudformation delete-stack --region "$REGION" --stack-name "${STACK_NAME:-aspare}"
aws cloudformation wait stack-delete-complete --region "$REGION" --stack-name "${STACK_NAME:-aspare}"
echo "Stack deleted."
