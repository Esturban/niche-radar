from __future__ import annotations

import csv
import json
import os
from pathlib import Path

from ..models import ProviderResult
from ..utils import shared_token_score


def collect_keyword_planner(terms: list[str]) -> ProviderResult:
    export_path = os.getenv("KEYWORD_PLANNER_EXPORT")
    if not export_path:
        return ProviderResult(
            provider="keyword_planner",
            status="unavailable",
            reason="KEYWORD_PLANNER_EXPORT is not set",
        )

    rows = _load_rows(Path(export_path))
    result = ProviderResult(provider="keyword_planner", status="ok", meta={"path": export_path})
    for term in terms:
        scored = sorted(
            (
                (
                    shared_token_score(term, row.get("keyword", row.get("query", ""))),
                    row,
                )
                for row in rows
                if row.get("keyword") or row.get("query")
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        best = [(score, row) for score, row in scored[:3] if score > 0]
        if best:
            top_row = best[0][1]
            result.hits[term] = [{"kind": "keyword_planner", "text": top_row.get("keyword", top_row.get("query", ""))}]
            result.metrics[term] = {
                "planner_volume": _to_float(top_row.get("avg_monthly_searches")),
                "planner_competition": _to_float(top_row.get("competition")),
            }

    if not result.hits:
        result.status = "unavailable"
        result.reason = "keyword planner export had no matching rows"
    return result


def _load_rows(path: Path) -> list[dict]:
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else data.get("rows", [])
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _to_float(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None

