from __future__ import annotations

import argparse
from pathlib import Path

from .models import RunConfig
from .pipeline import discover
from .utils import now_iso, slugify


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="niche-radar")
    subparsers = parser.add_subparsers(dest="command", required=True)

    discover_parser = subparsers.add_parser("discover", help="Discover rising niche territories.")
    discover_parser.add_argument("--resume", required=True, type=Path, help="Path to a markdown, text, or PDF profile.")
    discover_parser.add_argument("--topic", required=True, help="Topic seed to explore.")
    discover_parser.add_argument("--outdir", type=Path, help="Optional output directory.")
    discover_parser.add_argument("--max-clusters", type=int, default=12, help="Max ranked clusters to highlight.")
    discover_parser.add_argument("--with-search-console", action="store_true", help="Enable Search Console export enrichment.")
    discover_parser.add_argument("--with-keyword-planner", action="store_true", help="Enable Keyword Planner export enrichment.")
    discover_parser.add_argument("--geo", default="US", help="Geographic code for trend collection.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "discover":
        outdir = args.outdir or Path("runs") / f"{now_iso().replace(':', '').replace('+00:00', 'Z')}-{slugify(args.topic)}"
        config = RunConfig(
            resume_path=args.resume,
            topic=args.topic,
            outdir=outdir,
            max_clusters=args.max_clusters,
            geo=args.geo,
            with_search_console=args.with_search_console,
            with_keyword_planner=args.with_keyword_planner,
        )
        result = discover(config)
        print(f"wrote report to {result['outdir']}")
        if result["insufficient_signal"]:
            print("run completed with insufficient live signal; see report.md for details.")
        return 0

    parser.error("unknown command")
    return 2

