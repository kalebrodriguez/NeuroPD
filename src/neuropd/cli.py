"""Command-line entry point for NeuroPD.

During Milestone 0 the CLI exposes only introspection commands (version and
provenance). Pipeline subcommands (audit, preprocess, extract-features, train,
evaluate-external, report) are added in later milestones and will delegate to the
corresponding modules under :mod:`neuropd`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from neuropd import __version__
from neuropd.config import DEFAULT_SEED
from neuropd.logging import configure_logging
from neuropd.provenance import collect_provenance


def build_parser() -> argparse.ArgumentParser:
    """Construct the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="neuropd",
        description=(
            "NeuroPD research pipeline. Research tool only; not a medical device "
            "and not for diagnosis."
        ),
    )
    parser.add_argument("--version", action="version", version=f"neuropd {__version__}")
    parser.add_argument(
        "--log-level",
        default=None,
        help="Logging level (e.g. DEBUG, INFO, WARNING). Defaults to NEUROPD_LOG_LEVEL or INFO.",
    )

    sub = parser.add_subparsers(dest="command", required=False)

    p_prov = sub.add_parser(
        "provenance",
        help="Print a JSON provenance record (versions, platform, seed).",
    )
    p_prov.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed to record.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    if args.command == "provenance":
        json.dump(collect_provenance(seed=args.seed), sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
