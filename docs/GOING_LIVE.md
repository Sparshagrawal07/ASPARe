# Going live on AWS

> Everything that needs **your** AWS account. The code, tests and scripts are done; these steps cannot be automated
> because they need your credentials.

ASPARe has two independent live paths. Use either or both.

| Path | What it is | Cost / risk |
| --- | --- | --- |
| **A. Live dashboard** | Streamlit scans your real account **read-only**; you approve each fix | Free; writes only on approval, only to allowlisted + tagged buckets |
| **B. Event-driven deployment** | Lambdas react to CloudTrail S3 events and remediate automatically | A few cents/month; needs CloudTrail |

## 0. One-time: credentials

```bash
aws configure            # or: aws sso login --profile <name>
aws sts get-caller-identity
```

Use an IAM user/role that can read S3 config (`s3:Get*`, `s3:ListAllMyBuckets`). For path A remediation or path B
deployment it also needs write access to the buckets you allow plus CloudFormation/IAM/Lambda/EventBridge/SNS rights.
Never commit keys; `.env` is git-ignored.

## 1. Create a safe test bucket

ASPARe only changes buckets that are allowlisted **and** tagged `ASPAReDemo=true`.

```bash
BUCKET=aspare-test-$RANDOM-$USER
aws s3api create-bucket --bucket $BUCKET --region us-east-1
aws s3api put-bucket-tagging --bucket $BUCKET --tagging 'TagSet=[{Key=ASPAReDemo,Value=true}]'
# Make it deliberately insecure (public-access-block off):
aws s3api put-public-access-block --bucket $BUCKET --public-access-block-configuration \
  BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
```

## 2. Path A: live dashboard

```bash
export ASPARE_ALLOWED_BUCKETS=$BUCKET     # only this bucket can be remediated
streamlit run dashboard/app.py
```

In the sidebar choose **Live AWS** → **Connect** → **Scan**. Every bucket in the account is *inspected*; only
`$BUCKET` shows an enabled **Approve fix** button. Dry-run is on by default — switch it off and reconnect to apply
the fix for real. Approvals and verification results are written to `var/audit/live.jsonl`.

## 2b. The live showcase (best for presentations)

```bash
export ASPARE_REGION=ap-southeast-2     # a region your account allows
make showcase                           # then open "Live Showcase" in the left navigation
```

Choose a scenario (public access off, public-read policy, plain HTTP, no versioning, or all at once), pick
*Autonomous* or *Human-approved*, and press **Run showcase**. ASPARe creates an `aspare-showcase-*` bucket, breaks it
on purpose, then streams detection, risk reasoning, the fix, and a before/after verification read back from AWS. The
page ends with `aws s3api` commands and a console link as proof, plus a cleanup panel that deletes showcase buckets
(only those). Verified against a real account; ordering matters, so the HTTPS policy fix runs before the Public
Access Block (S3 will not save a policy containing a public statement once `BlockPublicPolicy` is on).

## 3. Path B: deploy the Lambdas

Requires an active CloudTrail trail with management events (console → CloudTrail → *Create trail*, or
`aws cloudtrail create-trail ...` + `start-logging`). Then:

```bash
scripts/deploy.sh $BUCKET aspare-code-$RANDOM aspare-audit-$RANDOM you@example.com
```

This packages the code, uploads it, deploys `infrastructure/aws/template.yaml` and prints the outputs. Confirm the
SNS subscription e-mail that AWS sends. Test it:

```bash
aws s3api put-public-access-block --bucket $BUCKET --public-access-block-configuration \
  BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false
# within ~1-5 minutes CloudTrail delivers the event, ASPARe re-enables the block, and writes audit/*.json to the audit bucket
aws logs tail /aws/lambda/aspare-detection --follow
```

Point the dashboard at the audit bucket: `ASPARE_AUDIT_BACKEND=s3 ASPARE_AUDIT_BUCKET=<audit-bucket> streamlit run dashboard/app.py`.

Clean up with `scripts/teardown.sh` (empty the versioned audit bucket first if you want it removed) and delete the
test bucket.

## 4. Optional: Claude analysis, Azure and Google Cloud

**Claude (LLM analysis).** Create an API key in the Anthropic Console and export it before starting the dashboard:

```bash
pip install -e ".[llm]"
export ANTHROPIC_API_KEY=...        # never commit this
export ASPARE_LLM_MODEL=claude-opus-5-5   # optional; this is the default
```

The Intelligence page then shows "Reasoner: Claude". Without a key it shows the offline reasoner. Each *Analyse* click
is one API call, so cost is under your control.

**Azure Blob Storage.** `pip install -e ".[azure]"`, `az login`, then:

```bash
export ASPARE_AZURE_SUBSCRIPTION_ID=<subscription-id>
export ASPARE_AZURE_RESOURCE_GROUP=<resource-group>
export ASPARE_ALLOWED_BUCKETS="azure://<storage-account>"
```

Tag the storage account `ASPAReDemo=true`. Needs Reader for scanning and Storage Account Contributor to remediate.

**Google Cloud Storage.** `pip install -e ".[gcp]"`, `gcloud auth application-default login`, then:

```bash
export ASPARE_GCP_ENABLED=true ASPARE_GCP_PROJECT=<project-id>
export ASPARE_ALLOWED_BUCKETS="gcs://<bucket>"
```

Label the bucket `asparedemo=true`. **The Azure and GCP SDK wrappers have only been tested against simulated APIs**, so
treat the first live run as a test and start with `--dry-run` style review of the findings.

## Known account-level caveats

- **CloudTrail to EventBridge in the test account:** the rule pattern matches a sample event and the trail logs and
  delivers to S3, but real-time delivery to the Lambda did not fire within 15 minutes there. A manual or hourly
  scheduled scan does fix the bucket. If real-time matters for your demo, verify it in your account before relying on it.

- **Region restrictions:** managed/sandbox accounts can restrict regions or services with organization policies.
  If `CreateBucket` returns `explicit deny in a service control policy`, try another region your organization allows.
- **Public ACLs:** accounts created after April 2023 block ACLs by default, so the ACL rule may report nothing.
- **Python runtime:** the template defaults to `python3.14`; if your region lacks it, deploy with
  `--parameter-overrides LambdaRuntime=python3.13` (edit `scripts/deploy.sh`).
- **CloudTrail delay:** management events take a few minutes; the hourly scheduled scan is a backstop.
- **Safety:** to widen the blast radius deliberately, set `ASPARE_ALLOWED_BUCKETS` / `ASPARE_REQUIRE_DEMO_TAG=false`.
  The defaults are intentionally conservative.
