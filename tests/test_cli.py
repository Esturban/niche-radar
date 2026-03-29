from __future__ import annotations

from pathlib import Path

from niche_radar.cli import build_parser
from niche_radar.ingest import load_profile, load_resume


def test_parser_accepts_discover_command():
    parser = build_parser()
    args = parser.parse_args(["discover", "--resume", "tests/fixtures/resume.md", "--topic", "creator education"])
    assert args.command == "discover"
    assert args.top_niches == 5
    assert args.topic == "creator education"


def test_load_resume_reads_markdown_fixture():
    text = load_resume(Path("tests/fixtures/resume.md"))
    assert "analytics workflows" in text


def test_load_profile_merges_resume_and_site(monkeypatch):
    pages = [
        {
            "url": "https://example.com",
            "title": "Home",
            "text": "workflow automation for service businesses",
            "links": ["/about"],
            "status_code": 200,
        },
        {
            "url": "https://example.com/about",
            "title": "About",
            "text": "reporting dashboards for operations teams",
            "links": [],
            "status_code": 200,
        },
    ]
    monkeypatch.setattr("niche_radar.ingest.load_site", lambda site_url, page_budget=4: pages)

    profile = load_profile(resume_path=Path("tests/fixtures/resume.md"), site_url="example.com")

    assert "analytics workflows" in profile.text
    assert "workflow automation for service businesses" in profile.text
    assert profile.metadata["site_url"] == "example.com"
