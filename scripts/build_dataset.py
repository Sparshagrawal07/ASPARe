#!/usr/bin/env python3
"""Build the ~40-bucket recorded inventory and CloudTrail event set."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAB_OFF = {
    "BlockPublicAcls": False,
    "IgnorePublicAcls": False,
    "BlockPublicPolicy": False,
    "RestrictPublicBuckets": False,
}
PAB_ON = {
    "BlockPublicAcls": True,
    "IgnorePublicAcls": True,
    "BlockPublicPolicy": True,
    "RestrictPublicBuckets": True,
}
AES = {"algorithm": "AES256", "bucket_key_enabled": True}


def https_policy(name: str) -> dict:
    arn = f"arn:aws:s3:::{name}"
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "ASPAReDenyInsecureTransport",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:*",
                "Resource": [arn, f"{arn}/*"],
                "Condition": {"Bool": {"aws:SecureTransport": "false"}},
            }
        ],
    }


def bucket(
    name: str,
    purpose: str,
    data_class: str,
    *,
    pab: dict,
    encryption: dict | None,
    versioning: str | None,
    policy: dict | None,
    acl: str,
    env: str = "lab",
) -> dict:
    return {
        "name": name,
        "region": "us-east-1",
        "tags": {
            "ASPAReDemo": "true",
            "DataClass": data_class,
            "Purpose": purpose,
            "Environment": env,
        },
        "public_access_block": pab,
        "encryption": encryption or {},
        "versioning": {"status": versioning},
        "policy": policy,
        "acl": acl,
    }


def event(event_id: str, when: datetime, name: str, api: str, extra: dict | None = None) -> dict:
    params = {"bucketName": name}
    if extra:
        params.update(extra)
    iso = when.strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": event_id,
        "source": "aws.s3",
        "detail-type": "AWS API Call via CloudTrail",
        "time": iso,
        "region": "us-east-1",
        "detail": {
            "eventVersion": "1.11",
            "eventSource": "s3.amazonaws.com",
            "eventName": api,
            "eventTime": iso,
            "awsRegion": "us-east-1",
            "eventID": event_id,
            "userIdentity": {
                "type": "Root",
                "accountId": "123456789012",
                "arn": "arn:aws:iam::123456789012:root",
            },
            "requestParameters": params,
            "readOnly": False,
            "eventType": "AwsApiCall",
        },
    }


def main() -> None:
    originals = [
        bucket(
            "ferpa-student-record-demo-for-cap",
            "student-record-lab",
            "FERPA",
            pab=PAB_OFF,
            encryption=AES,
            versioning=None,
            policy=None,
            acl="private",
        ),
        bucket(
            "ferpa-remediation-results-cap",
            "remediation-results",
            "FERPA",
            pab=PAB_OFF,
            encryption=AES,
            versioning=None,
            policy=None,
            acl="private",
        ),
    ]
    extras: list[dict] = []
    specs = [
        ("ferpa-transcripts-raw-east", "transcripts", "FERPA", "pab", "prod"),
        ("ferpa-enrollment-exports", "enrollment", "FERPA", "pab", "prod"),
        ("ferpa-advising-notes-2026", "advising", "FERPA", "full", "prod"),
        ("ferpa-financial-aid-packets", "finaid", "FERPA", "acl", "prod"),
        ("campus-id-card-photos", "id-photos", "PII", "full", "prod"),
        ("registrar-degree-audit", "degree-audit", "FERPA", "pab", "prod"),
        ("housing-contracts-scan", "housing", "PII", "enc", "prod"),
        ("hr-onboarding-docs", "hr", "PII", "https", "prod"),
        ("payroll-yearend-archive", "payroll", "FINANCIAL", "full", "prod"),
        ("alumni-giving-exports", "advancement", "PII", "pab", "prod"),
        ("research-irb-consents", "irb", "PHI", "acl", "prod"),
        ("clinic-billing-extracts", "clinic", "PHI", "enc", "prod"),
        ("library-patron-holds", "library", "PII", "https", "prod"),
        ("its-cloudtrail-archive", "audit-logs", "AUDIT", "vers", "prod"),
        ("its-vpc-flow-logs", "net-logs", "AUDIT", "https", "prod"),
        ("its-config-snapshots", "config", "AUDIT", "enc", "prod"),
        ("backup-rds-snapshots-s3", "db-backups", "BACKUP", "full", "prod"),
        ("backup-home-directories", "home-dirs", "PII", "pab", "prod"),
        ("analytics-clickstream-raw", "analytics", "INTERNAL", "enc", "prod"),
        ("analytics-sis-warehouse", "warehouse", "FERPA", "https", "prod"),
        ("data-lake-landing-zone", "datalake", "INTERNAL", "pab", "prod"),
        ("ml-feature-store-staging", "ml", "INTERNAL", "enc", "staging"),
        ("ci-artifacts-github-runners", "ci", "INTERNAL", "acl", "dev"),
        ("ci-cache-npm-wheels", "ci-cache", "INTERNAL", "vers", "dev"),
        ("app-uploads-student-portal", "uploads", "FERPA", "full", "prod"),
        ("app-static-marketing-site", "marketing", "PUBLIC", "https", "prod"),
        ("media-commencement-video", "media", "INTERNAL", "enc", "prod"),
        ("finance-1098t-batch", "tax", "FINANCIAL", "full", "prod"),
        ("legal-hold-ediscovery", "legal", "LEGAL", "pab", "prod"),
        ("vendor-sftp-dropbox", "vendor-sftp", "PII", "acl", "prod"),
        ("shared-scratch-sandbox", "scratch", "INTERNAL", "full", "dev"),
        ("old-glacier-restore-cache", "restore", "BACKUP", "vers", "prod"),
        ("observability-otel-export", "otel", "AUDIT", "https", "prod"),
        ("terraform-state-shared", "tfstate", "SECRETS", "enc", "prod"),
        ("lambda-deployment-zips", "lambda", "INTERNAL", "vers", "prod"),
        ("quarantine-macie-findings", "macie", "SENSITIVE", "pab", "prod"),
        ("dr-replica-us-west-exp", "dr", "BACKUP", "https", "prod"),
        ("tmp-data-science-scratch", "ds-scratch", "INTERNAL", "full", "dev"),
    ]
    for name, purpose, data_class, profile, env in specs:
        if profile == "pab":
            extras.append(bucket(name, purpose, data_class, pab=PAB_OFF, encryption=AES, versioning=None, policy=None, acl="private", env=env))
        elif profile == "enc":
            extras.append(bucket(name, purpose, data_class, pab=PAB_ON, encryption=None, versioning=None, policy=None, acl="private", env=env))
        elif profile == "https":
            extras.append(bucket(name, purpose, data_class, pab=PAB_ON, encryption=AES, versioning="Enabled", policy=None, acl="private", env=env))
        elif profile == "vers":
            extras.append(bucket(name, purpose, data_class, pab=PAB_ON, encryption=AES, versioning=None, policy=https_policy(name), acl="private", env=env))
        elif profile == "acl":
            extras.append(bucket(name, purpose, data_class, pab=PAB_OFF, encryption=AES, versioning=None, policy=None, acl="public-read", env=env))
        elif profile == "full":
            extras.append(bucket(name, purpose, data_class, pab=PAB_OFF, encryption=None, versioning=None, policy=None, acl="private", env=env))
        else:
            raise ValueError(profile)

    # Two locked-down buckets so the estate is not 100% broken.
    extras.append(
        bucket(
            "security-aspare-audit-safe",
            "aspare-audit",
            "AUDIT",
            pab=PAB_ON,
            encryption=AES,
            versioning="Enabled",
            policy=https_policy("security-aspare-audit-safe"),
            acl="private",
            env="prod",
        )
    )
    extras.append(
        bucket(
            "security-config-baseline-safe",
            "baseline",
            "AUDIT",
            pab=PAB_ON,
            encryption=AES,
            versioning="Enabled",
            policy=https_policy("security-config-baseline-safe"),
            acl="private",
            env="prod",
        )
    )

    buckets = originals + extras
    start = datetime(2026, 4, 5, 17, 40, tzinfo=UTC)
    events = [
        event(
            "d111de18-0cf9-4b6f-a96a-9c4612e3f417",
            datetime(2026, 4, 5, 18, 2, 9, tzinfo=UTC),
            "ferpa-remediation-results-cap",
            "PutBucketPublicAccessBlock",
            {"PublicAccessBlockConfiguration": dict(PAB_OFF)},
        ),
        event(
            "029c58f6-38c2-4703-9ebb-b15c7d9d6f89",
            datetime(2026, 4, 5, 18, 53, 20, tzinfo=UTC),
            "ferpa-student-record-demo-for-cap",
            "PutBucketPublicAccessBlock",
            {"PublicAccessBlockConfiguration": dict(PAB_OFF)},
        ),
    ]
    api_for = {
        "pab": "PutBucketPublicAccessBlock",
        "enc": "DeleteBucketEncryption",
        "https": "DeleteBucketPolicy",
        "vers": "PutBucketVersioning",
        "acl": "PutBucketAcl",
        "full": "CreateBucket",
        "safe": "CreateBucket",
    }
    extra_for = {
        "pab": {"PublicAccessBlockConfiguration": dict(PAB_OFF)},
        "acl": {"x-amz-acl": "public-read"},
        "vers": {"VersioningConfiguration": {"Status": "Suspended"}},
    }
    profiles = [spec[3] for spec in specs] + ["safe", "safe"]
    for index, (bucket_doc, profile) in enumerate(zip(extras, profiles, strict=True), start=3):
        when = start + timedelta(minutes=index * 7)
        events.append(
            event(
                f"ct-estate-{index:02d}-{bucket_doc['name'][:18]}",
                when,
                bucket_doc["name"],
                api_for[profile],
                extra_for.get(profile),
            )
        )

    inventory = {
        "source": (
            "April 2026 CloudTrail LookupEvents and GetBucket* captures for the two FERPA lab "
            "buckets, plus a reconstructed 40-bucket campus estate using the same control fields."
        ),
        "region": "us-east-1",
        "buckets": buckets,
    }
    trail = {
        "source": "Sanitized CloudTrail management events. Access keys and the real account id were removed.",
        "events": events,
    }
    (ROOT / "data" / "inventory" / "s3-buckets.json").write_text(json.dumps(inventory, indent=2) + "\n")
    (ROOT / "data" / "cloudtrail" / "s3-lookup-events.json").write_text(json.dumps(trail, indent=2) + "\n")
    print(f"wrote {len(buckets)} buckets and {len(events)} events")


if __name__ == "__main__":
    main()
