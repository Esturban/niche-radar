from __future__ import annotations

import json
from pathlib import Path


def compare_runs(left: Path, right: Path, top_n: int = 5) -> str:
    left_meta, left_clusters = _load_run(left)
    right_meta, right_clusters = _load_run(right)

    left_titles = [cluster.get("title", cluster.get("title_seed", "")) for cluster in left_clusters[:top_n]]
    right_titles = [cluster.get("title", cluster.get("title_seed", "")) for cluster in right_clusters[:top_n]]
    added = [title for title in right_titles if title and title not in left_titles]
    removed = [title for title in left_titles if title and title not in right_titles]

    lines = [
        "# niche-radar run comparison",
        "",
        f"- Left run: `{left}`",
        f"- Right run: `{right}`",
        f"- Left focus: `{left_meta.get('focus') or 'profile-driven'}`",
        f"- Right focus: `{right_meta.get('focus') or 'profile-driven'}`",
        "",
        "## Top cluster delta",
        f"- Added on right: `{', '.join(added) if added else 'none'}`",
        f"- Removed from left: `{', '.join(removed) if removed else 'none'}`",
        "",
        "## Gate delta",
        _gate_line("Focus-qualified clusters", left_meta, right_meta, "focus_summary", "accepted_clusters"),
        _gate_line("Evidence-qualified clusters", left_meta, right_meta, "evidence_summary", "accepted_clusters"),
        _gate_line("Recommended bets", left_meta, right_meta, "wedge_summary", "recommended_bet_count"),
        "",
        "## Right run top clusters",
    ]
    for cluster in right_clusters[:top_n]:
        lines.append(
            f"- {cluster.get('title', cluster.get('title_seed', 'unknown'))}: "
            f"focus `{cluster.get('focus_score', 0.0):.2f}` / evidence `{cluster.get('evidence_gate', False)}` / "
            f"recommended `{cluster.get('recommended_bet', False)}`"
        )
    return "\n".join(lines) + "\n"


def _load_run(path: Path) -> tuple[dict, list[dict]]:
    run_meta = json.loads((path / "run_meta.json").read_text(encoding="utf-8"))
    clusters = json.loads((path / "clusters.json").read_text(encoding="utf-8"))
    return run_meta, clusters


def _gate_line(label: str, left_meta: dict, right_meta: dict, section: str, field: str) -> str:
    left_value = _resolve_gate_value(left_meta, section, field)
    right_value = _resolve_gate_value(right_meta, section, field)
    return f"- {label}: `{left_value}` -> `{right_value}`"


def _resolve_gate_value(run_meta: dict, section: str, field: str) -> int:
    value = run_meta.get(section, {}).get(field, 0)
    if isinstance(value, list):
        return len(value)
    return int(value or 0)
