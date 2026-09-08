"""Command-line demo entrypoint."""

from __future__ import annotations

import argparse
import sys

from aspare.demo import run_live_demo, run_mocked_demo


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="ASPARe demonstration: detect, remediate, verify, and audit S3 misconfigurations"
    )
    parser.add_argument(
        "--mode",
        choices=("mocked", "live"),
        default="mocked",
        help="mocked uses moto (no real AWS). live creates a uniquely named demo bucket.",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help="Live mode requires the exact token ASPARE-LIVE-DEMO",
    )
    parser.add_argument("--cleanup", action="store_true", help="Delete the live demo bucket after a successful run")
    args = parser.parse_args(argv)
    if args.mode == "mocked":
        run_mocked_demo()
        return 0
    run_live_demo(confirm=args.confirm, cleanup=args.cleanup)
    return 0


if __name__ == "__main__":
    sys.exit(main())
