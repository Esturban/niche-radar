from __future__ import annotations

from pathlib import Path

from niche_radar.cli import build_parser
from niche_radar.ingest import load_resume


def test_parser_accepts_discover_command():
    parser = build_parser()
    args = parser.parse_args(["discover", "--resume", "tests/fixtures/resume.md", "--topic", "creator education"])
    assert args.command == "discover"
    assert args.max_clusters == 12


def test_load_resume_reads_markdown_fixture():
    text = load_resume(Path("tests/fixtures/resume.md"))
    assert "analytics workflows" in text

