from __future__ import annotations

import csv
import json
from pathlib import Path

from .utils import now_iso


def write_outputs(
    outdir: Path,
    clusters: list[dict],
    all_terms: list[dict],
    question_graph: dict,
    evidence: list[dict],
    provider_results: list[dict],
    run_meta: dict,
    top_niches: int,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    top_clusters = clusters[:top_niches]
    dropped_clusters = clusters[top_niches:]

    (outdir / "report.md").write_text(render_report(top_clusters, dropped_clusters, run_meta), encoding="utf-8")
    (outdir / "clusters.json").write_text(json.dumps(top_clusters, indent=2), encoding="utf-8")
    (outdir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    (outdir / "question_graph.json").write_text(json.dumps(question_graph, indent=2), encoding="utf-8")
    (outdir / "provider_hits.json").write_text(json.dumps(provider_results, indent=2), encoding="utf-8")
    (outdir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    _write_terms_csv(outdir / "terms.csv", all_terms)
    _write_trends_csv(outdir / "trends.csv", all_terms)


def append_run_index(root: Path, record: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "index.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"recorded_at": now_iso(), **record}) + "\n")


def render_report(top_clusters: list[dict], dropped_clusters: list[dict], run_meta: dict) -> str:
    focus = run_meta.get("focus") or "profile-driven"
    source_labels = []
    if run_meta.get("resume_path"):
        source_labels.append(run_meta["resume_path"])
    if run_meta.get("site_url"):
        source_labels.append(run_meta["site_url"])

    lines = [
        "# niche-radar report",
        "",
        "## Executive summary",
        f"- Focus bias: `{focus}`",
        f"- Profile sources: `{', '.join(source_labels) if source_labels else 'profile-driven'}`",
        f"- Confidence floor: `{run_meta['confidence_floor']}`",
        "- This report ranks up to five niches from strongest evidence to weakest evidence.",
        "- External evidence is the backbone. Profile fit is a filter.",
        "- It does not validate market demand, willingness to pay, or lack of saturation.",
        "",
        "## Top niches",
        "",
        "| Niche | Evidence | Confidence | Fit | Citations |",
        "|---|---:|---:|---:|---:|",
    ]
    for cluster in top_clusters:
        lines.append(
            f"| {cluster['title']} | {cluster['evidence_strength']:.2f} ({cluster['evidence_tier']}) | {cluster['confidence']:.2f} | {cluster['profile_fit_score']:.2f} | {cluster['citation_count']} |"
        )

    for cluster in top_clusters:
        lines.extend(
            [
                "",
                f"## {cluster['title']}",
                "",
                f"- Evidence tier: `{cluster['evidence_tier']}`",
                f"- Evidence strength: `{cluster['evidence_strength']:.2f}`",
                f"- Citation count: `{cluster['citation_count']}`",
                f"- Surface count: `{cluster['surface_count']}`",
                f"- Profile fit score: `{cluster['profile_fit_score']:.2f}`",
                f"- Trend strength: `{cluster['trend_strength']:.2f}`",
                f"- Recency support: `{cluster['recency_support']:.2f}`",
                f"- Confidence: `{cluster['confidence']:.2f}`",
                "",
                "### Why it fits",
                f"- Connected roots: {', '.join(cluster['lineage_roots'])}",
                f"- Generations represented: {', '.join(str(value) for value in cluster['generations'])}",
                "",
                "### Why it surfaced externally",
                f"- Representative terms: {', '.join(cluster['terms'][:6])}",
                f"- Recurring related terms: {', '.join(cluster['related_terms'][:6]) if cluster['related_terms'] else 'No strong related-term signal captured.'}",
                "",
                "### Common question patterns",
            ]
        )
        if cluster["questions"]:
            lines.extend(f"- {question}" for question in cluster["questions"][:8])
        else:
            lines.append("- No strong question pattern surfaced from the active providers.")

        lines.extend(["", "### Supporting evidence"])
        if cluster["evidence"]:
            for item in cluster["evidence"][:5]:
                lines.append(f"- [{item['title']}]({item['url']}): {item['snippet']}")
        else:
            lines.append("- No public evidence pages were captured for this niche in this run.")

        lines.extend(
            [
                "",
                "### Suggested wedge",
                f"- {cluster['suggested_wedge']}",
                "",
                "### What this does not prove",
                "- It does not prove validated demand.",
                "- It does not prove low competition or willingness to pay.",
                "- It does not prove the cluster is unsaturated.",
                "",
                "### Next validation step",
                f"- Talk to 3 operators in `{cluster['title']}` and test whether the cited problems map to active pain worth paying to fix.",
            ]
        )

    lines.extend(["", "## Lower-ranked niches", ""])
    if dropped_clusters:
        for cluster in dropped_clusters[:8]:
            lines.append(
                f"- {cluster['title']}: lower-ranked because evidence `{cluster['evidence_strength']:.2f}` / confidence `{cluster['confidence']:.2f}` was weaker."
            )
    else:
        lines.append("- No dropped clusters in this run.")

    return "\n".join(lines) + "\n"


def _write_terms_csv(path: Path, all_terms: list[dict]) -> None:
    fieldnames = [
        "term",
        "generation",
        "lineage_root",
        "parent_term",
        "source",
        "trend_strength_raw",
        "trend_velocity_raw",
        "adjacency_count_raw",
        "question_density_raw",
        "surface_spread_raw",
        "providers",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in all_terms:
            writer.writerow(
                {
                    "term": item["term"],
                    "generation": item.get("generation"),
                    "lineage_root": item.get("lineage_root"),
                    "parent_term": item.get("parent_term"),
                    "source": item.get("source"),
                    "trend_strength_raw": item.get("trend_strength_raw"),
                    "trend_velocity_raw": item.get("trend_velocity_raw"),
                    "adjacency_count_raw": item.get("adjacency_count_raw"),
                    "question_density_raw": item.get("question_density_raw"),
                    "surface_spread_raw": item.get("surface_spread_raw"),
                    "providers": ",".join(item.get("providers", [])),
                }
            )


def _write_trends_csv(path: Path, all_terms: list[dict]) -> None:
    fieldnames = ["term", "trend_strength_raw", "trend_velocity_raw", "trend_calibrated"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in all_terms:
            writer.writerow(
                {
                    "term": item["term"],
                    "trend_strength_raw": item.get("trend_strength_raw"),
                    "trend_velocity_raw": item.get("trend_velocity_raw"),
                    "trend_calibrated": item.get("trend_calibrated"),
                }
            )
