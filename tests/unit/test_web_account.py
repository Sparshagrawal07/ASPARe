"""Hosted-product engine path: scan and fix a real (moto-simulated) AWS account with STS-style credentials."""

import hashlib
import hmac
import sys
import time
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "web" / "api"))

import engine  # noqa: E402
from _lib import service  # noqa: E402

CREDS = {"accessKeyId": "AKIATESTTESTTESTTEST", "secretAccessKey": "secret", "sessionToken": "token"}
PAB_OFF = {
    "BlockPublicAcls": False,
    "IgnorePublicAcls": False,
    "BlockPublicPolicy": False,
    "RestrictPublicBuckets": False,
}


def _body(**extra):
    return {"credentials": CREDS, "region": "us-east-1", **extra}


@pytest.fixture
def account():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        for name, optin in (("optin-bucket", True), ("plain-bucket", False)):
            s3.create_bucket(Bucket=name)
            s3.put_bucket_tagging(
                Bucket=name, Tagging={"TagSet": [{"Key": "aspare-autofix", "Value": "true" if optin else "no"}]}
            )
            s3.put_public_access_block(Bucket=name, PublicAccessBlockConfiguration=PAB_OFF)
        yield s3


def test_scan_reports_findings_inventory_and_which_fixes_are_allowed(account):
    out = service.scan_account(_body())
    assert out["summary"]["buckets"] == 2 and out["summary"]["total"] >= 2
    inv = {i["name"]: i for i in out["inventory"]}
    assert inv["optin-bucket"]["autofixOptIn"] and not inv["plain-bucket"]["autofixOptIn"]
    pub = {f["resource"]: f for f in out["findings"] if f["rule"] == "S3_PUBLIC_ACCESS"}
    assert pub["optin-bucket"]["autofixAllowed"] is True and pub["plain-bucket"]["autofixAllowed"] is False
    # scanning is read-only
    assert (
        account.get_public_access_block(Bucket="optin-bucket")["PublicAccessBlockConfiguration"]["BlockPublicAcls"]
        is False
    )


def test_remediation_fixes_opted_in_buckets_and_refuses_the_rest(account):
    scan = service.scan_account(_body())
    ids = [f["id"] for f in scan["findings"] if f["rule"] == "S3_PUBLIC_ACCESS"]
    out = service.remediate_account(_body(findingIds=ids, buckets=["optin-bucket", "plain-bucket"]))
    by = {o["resource"]: o for o in out["outcomes"]}
    assert by["optin-bucket"]["verified"] is True
    assert by["plain-bucket"]["verified"] is False and by["plain-bucket"]["status"] == "DENIED"
    assert (
        account.get_public_access_block(Bucket="optin-bucket")["PublicAccessBlockConfiguration"]["BlockPublicAcls"]
        is True
    )
    assert (
        account.get_public_access_block(Bucket="plain-bucket")["PublicAccessBlockConfiguration"]["BlockPublicAcls"]
        is False
    )


def test_allow_list_narrows_what_may_be_changed(account):
    scan = service.scan_account(_body(allowedBuckets=["plain-bucket"]))
    ids = [f["id"] for f in scan["findings"]]
    out = service.remediate_account(_body(allowedBuckets=["plain-bucket"], findingIds=ids, buckets=["optin-bucket"]))
    assert all(not o["verified"] for o in out["outcomes"])  # opted in, but outside the allow-list


@pytest.mark.parametrize(
    "bad",
    [
        {"credentials": {}},
        {"credentials": CREDS, "region": "not-a-region"},
        {"credentials": CREDS, "region": "us-east-1", "allowedBuckets": ["Bad Name"]},
    ],
)
def test_bad_requests_are_rejected(bad):
    with pytest.raises(service.ValidationError):
        service.scan_account(bad)


def test_engine_signature_scheme():
    body = b'{"action":"scan"}'
    ts = str(int(time.time()))
    sig = hmac.new(b"s3cret", ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    assert engine.verify("s3cret", ts, sig, body)
    assert not engine.verify("other", ts, sig, body)
    assert not engine.verify("s3cret", ts, sig, body + b" ")
    assert not engine.verify("s3cret", str(int(time.time()) - 3600), sig, body)
    assert not engine.verify("s3cret", "x", sig, body)


def test_untagged_bucket_is_not_an_inspection_error(account):
    account.create_bucket(Bucket="no-tags-at-all")
    account.put_public_access_block(Bucket="no-tags-at-all", PublicAccessBlockConfiguration=PAB_OFF)
    out = service.scan_account(_body())
    hit = next(f for f in out["findings"] if f["resource"] == "no-tags-at-all" and f["rule"] == "S3_PUBLIC_ACCESS")
    assert hit["confidence"] >= 0.9, hit["reasons"]
    assert not any("Inspection reported" in r for r in hit["reasons"])
