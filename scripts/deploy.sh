#!/usr/bin/env bash
# Deploy ASPARe to AWS. Usage:
#   scripts/deploy.sh <allowed-bucket> <code-bucket> <audit-bucket> [alert-email]
# Needs AWS credentials (aws configure / aws sso login). All buckets must already be globally unique names;
# <allowed-bucket> must exist and be tagged ASPAReDemo=true (the only bucket ASPARe may remediate).
set -euo pipefail
cd "$(dirname "$0")/.."
ALLOWED=${1:?allowed bucket}
CODE=${2:?code bucket}
AUDIT=${3:?audit bucket (created by the stack)}
EMAIL=${4:-}
REGION=${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}
STACK=${STACK_NAME:-aspare}
RUNTIME=${LAMBDA_RUNTIME:-python3.13}

aws sts get-caller-identity >/dev/null
aws s3api head-bucket --bucket "$CODE" 2>/dev/null || {
  if [ "$REGION" = "us-east-1" ]; then aws s3api create-bucket --bucket "$CODE" --region "$REGION"
  else aws s3api create-bucket --bucket "$CODE" --region "$REGION" --create-bucket-configuration LocationConstraint="$REGION"; fi
  aws s3api put-public-access-block --bucket "$CODE" \
    --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
}
scripts/package_lambda.sh
aws s3 cp dist/lambda.zip "s3://$CODE/aspare/lambda.zip"
aws cloudformation deploy --region "$REGION" --stack-name "$STACK" \
  --template-file infrastructure/aws/template.yaml --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides AllowedBucketName="$ALLOWED" AuditBucketName="$AUDIT" CodeBucket="$CODE" \
    ScheduleEnabled=ENABLED DetectionRuleState=ENABLED AlertEmail="$EMAIL" LambdaRuntime="$RUNTIME"
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" --query "Stacks[0].Outputs" --output table
echo "Done. Confirm the SNS e-mail subscription if you passed an address."
