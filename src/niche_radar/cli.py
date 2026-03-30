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
    discover_parser.add_argument("--resume", type=Path, help="Path to a markdown, text, or PDF profile.")
    discover_parser.add_argument("--site", help="Optional website URL to use as a profile source.")
    discover_parser.add_argument("--focus", help="Optional niche bias to guide ranking and term expansion.")
    discover_parser.add_argument("--topic", help="Deprecated alias for --focus.")
    discover_parser.add_argument("--outdir", type=Path, help="Optional output directory.")
    discover_parser.add_argument("--top-niches", type=int, default=5, help="Max ranked niches to highlight.")
    discover_parser.add_argument("--max-clusters", type=int, help="Deprecated alias for --top-niches.")
    discover_parser.add_argument("--evidence-pages", type=int, default=3, help="Max public evidence pages to fetch per niche.")
    discover_parser.add_argument("--with-search-console", action="store_true", help="Enable Search Console export enrichment.")
    discover_parser.add_argument("--with-keyword-planner", action="store_true", help="Enable Keyword Planner export enrichment.")
    discover_parser.add_argument("--geo", default="US", help="Geographic code for trend collection.")
    discover_parser.add_argument(
        "--research-depth",
        choices=["off", "standard", "deep"],
        default="standard",
        help="Control the bounded post-shortlist research pass.",
    )
    discover_parser.add_argument(
        "--research-top-k",
        type=int,
        default=3,
        help="How many ranked niches to send through the research graph.",
    )
    discover_parser.add_argument(
        "--persist-trace",
        action="store_true",
        help="Write debug trace artifacts for the research graph.",
    )
    discover_parser.add_argument(
        "--llm-provider",
        default="openai",
        help="LLM provider used by the research graph. Only openai is supported in v1.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "discover":
        focus = args.focus or args.topic or ""
        if not args.resume and not args.site:
            parser.error("discover requires at least one of --resume or --site")
        top_niches = args.max_clusters or args.top_niches
        slug_source = focus or args.site or (args.resume.stem if args.resume else "profile-driven")
        run_slug = slugify(slug_source)
        outdir = args.outdir or Path("runs") / f"{now_iso().replace(':', '').replace('+00:00', 'Z')}-{run_slug}"
        config = RunConfig(
            resume_path=args.resume,
            site_url=args.site,
            focus=focus,
            outdir=outdir,
            top_niches=top_niches,
            evidence_pages=args.evidence_pages,
            geo=args.geo,
            with_search_console=args.with_search_console,
            with_keyword_planner=args.with_keyword_planner,
            research_depth=args.research_depth,
            research_top_k=args.research_top_k,
            persist_trace=args.persist_trace,
            llm_provider=args.llm_provider,
        )
        result = discover(config)
        print(f"wrote report to {result['outdir']}")
        if result["insufficient_signal"]:
            print("run completed with insufficient live signal; see report.md for details.")
        return 0

    parser.error("unknown command")
    return 2
