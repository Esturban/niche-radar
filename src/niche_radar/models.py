from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RunConfig:
    resume_path: Path | None
    site_url: str | None
    focus: str
    outdir: Path
    top_niches: int = 5
    evidence_pages: int = 3
    geo: str = "US"
    generations: int = 3
    with_search_console: bool = False
    with_keyword_planner: bool = False
    research_depth: str = "standard"
    research_top_k: int = 3
    persist_trace: bool = False
    llm_provider: str = "openai"


@dataclass(slots=True)
class ProviderResult:
    provider: str
    status: str
    reason: str | None = None
    metrics: dict[str, dict] = field(default_factory=dict)
    hits: dict[str, list[dict]] = field(default_factory=dict)
    meta: dict = field(default_factory=dict)


@dataclass(slots=True)
class TermRecord:
    term: str
    generation: int
    source: str
    lineage_root: str
    parent_term: str | None = None
