from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from ..models import ProviderResult
from ..utils import shared_token_score


def collect_search_console(terms: list[str]) -> ProviderResult:
    export_path = os.getenv("SEARCH_CONSOLE_EXPORT")
    if not export_path:
        return ProviderResult(
            provider="search_console",
            status="unavailable",
            reason="SEARCH_CONSOLE_EXPORT is not set",
        )

    rows = _load_rows(Path(export_path))
    result = ProviderResult(provider="search_console", status="ok", meta={"path": export_path})

    for term in terms:
        scored = sorted(
            (
                (
                    shared_token_score(term, row.get("query", "")),
                    row,
                )
                for row in rows
                if row.get("query")
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        best = [row for score, row in scored[:5] if score > 0]
        if best:
            result.hits[term] = [{"kind": "search_console", "text": row["query"], "clicks": row.get("clicks"), "impressions": row.get("impressions")} for row in best]
            result.metrics[term] = {"search_console_proximity": scored[0][0]}

    if not result.hits:
        result.status = "unavailable"
        result.reason = "search console export had no matching queries"
    return result


def _load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("rows", [])

    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))

