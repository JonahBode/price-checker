"""Command line interface for price_checker."""

from __future__ import annotations

import argparse
import csv
import sys
from typing import List, Optional, TextIO

from .checker import CheckReport, run_check
from .config import load_config


def _format_report(report: CheckReport) -> str:
    lines = [f"== {report.target.name} ({report.target.url}) =="]
    for region_result in report.region_results:
        if region_result.ok:
            price = region_result.result.price
            currency = region_result.result.currency or report.target.currency_hint or ""
            lines.append(f"  {region_result.region.name:<15} {currency} {price:.2f}")
        else:
            lines.append(f"  {region_result.region.name:<15} ERROR: {region_result.error}")

    cheapest = report.cheapest
    if cheapest is not None:
        lines.append(
            f"  -> cheapest region: {cheapest.region.name} "
            f"({cheapest.result.price:.2f}, spread {report.spread:.2f})"
        )
    else:
        lines.append("  -> no successful results")

    return "\n".join(lines)


def _write_csv(reports: List[CheckReport], fh: TextIO) -> None:
    writer = csv.writer(fh)
    writer.writerow(["target", "url", "region", "price", "currency", "error"])
    for report in reports:
        for region_result in report.region_results:
            if region_result.ok:
                writer.writerow(
                    [
                        report.target.name,
                        report.target.url,
                        region_result.region.name,
                        region_result.result.price,
                        region_result.result.currency or "",
                        "",
                    ]
                )
            else:
                writer.writerow(
                    [
                        report.target.name,
                        report.target.url,
                        region_result.region.name,
                        "",
                        "",
                        region_result.error,
                    ]
                )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="price_checker",
        description=(
            "Check a set of web pages for dynamic pricing differences across "
            "regions/VPN exit points."
        ),
    )
    parser.add_argument("config", help="Path to a JSON config file (see README).")
    parser.add_argument(
        "--csv",
        metavar="PATH",
        help="Write machine-readable results to PATH as CSV (use '-' for stdout).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-request timeout in seconds (default: 20).",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    config = load_config(args.config)
    reports = run_check(config.targets, config.regions, timeout=args.timeout)

    for report in reports:
        print(_format_report(report))
        print()

    if args.csv:
        if args.csv == "-":
            _write_csv(reports, sys.stdout)
        else:
            with open(args.csv, "w", newline="", encoding="utf-8") as fh:
                _write_csv(reports, fh)

    any_success = any(report.successful for report in reports)
    return 0 if any_success else 1


if __name__ == "__main__":
    sys.exit(main())
