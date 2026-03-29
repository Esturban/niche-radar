from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RunConfig:
    resume_path: Path
    topic: str
    outdir: Path
    max_clusters: int = 12
    geo: str = "US"
    generations: int = 3
    with_search_console: bool = False
    with_keyword_planner: bool = False


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

