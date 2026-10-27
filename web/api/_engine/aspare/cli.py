"""Command-line demo entrypoint."""

from __future__ import annotations

import argparse
import sys

from aspare.dataset import run_dataset_pipeline
from aspare.demo import run_live_demo, run_mocked_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ASPARe demonstration: detect, remediate, verify, and audit S3 misconfigurations"
    )
    parser.add_argument(
        "--mode",
        choices=("dataset", "mocked", "live", "policy", "benchmark"),
        default="dataset",
        help="dataset replays recorded CloudTrail lookups; mocked synthesizes a bucket; live creates one AWS bucket; "
        "policy prints least-privilege IAM policies; benchmark compares rule-only vs fused triage.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Live mode requires the exact token ASPARE-LIVE-DEMO",
    )
    parser.add_argument("--bucket", default="", help="policy mode: comma-separated buckets ASPARe may modify")
    parser.add_argument("--audit-bucket", default="", help="policy mode: audit bucket name")
    parser.add_argument("--cleanup", action="store_true", help="Delete the live demo bucket after a successful run")
    args = parser.parse_args(argv)
    if args.mode == "policy":
        from aspare.policygen import generate_policies

        buckets = [b.strip() for b in args.bucket.split(",") if b.strip()]
        if not buckets:
            raise SystemExit("--mode policy requires --bucket <name[,name...]>")
        for policy in generate_policies(buckets, audit_bucket=args.audit_bucket or None).values():
            print(policy.to_json())
        return 0
    if args.mode == "benchmark":
        import runpy
        from pathlib import Path

        runpy.run_path(str(Path(__file__).resolve().parents[2] / "scripts" / "benchmark.py"), run_name="__main__")
        return 0
    if args.mode == "dataset":
        run_dataset_pipeline()
        return 0
    if args.mode == "mocked":
        run_mocked_demo()
        return 0
    run_live_demo(confirm=args.confirm, cleanup=args.cleanup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
