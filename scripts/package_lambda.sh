#!/usr/bin/env bash
# Build dist/lambda.zip: the aspare package + config/ (policies, risk policy, explainers).
# boto3 is provided by the Lambda runtime, so nothing is vendored.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf build/lambda dist/lambda.zip
mkdir -p build/lambda dist
cp -R src/aspare build/lambda/aspare
cp -R config build/lambda/config
find build/lambda -name "__pycache__" -type d -prune -exec rm -rf {} +
(cd build/lambda && zip -qr ../../dist/lambda.zip .)
echo "Built dist/lambda.zip ($(du -h dist/lambda.zip | cut -f1))"
