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
    provider_results: list[dict],
    run_meta: dict,
    max_clusters: int,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    top_clusters = clusters[:max_clusters]
    dropped_clusters = clusters[max_clusters:]

    (outdir / "report.md").write_text(render_report(top_clusters, dropped_clusters, run_meta), encoding="utf-8")
    (outdir / "clusters.json").write_text(json.dumps(top_clusters, indent=2), encoding="utf-8")
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
    lines = [
        "# niche-radar report",
        "",
        "## Executive summary",
        f"- Topic seed: `{run_meta['topic']}`",
        f"- Resume/profile: `{run_meta['resume_path']}`",
        f"- Confidence floor: `{run_meta['confidence_floor']}`",
        "- This report identifies rising or resilient keyword territories and recurring questions.",
        "- It does not validate market demand, willingness to pay, or lack of saturation.",
        "",
        "## Top niche territories",
        "",
        "| Cluster | Score | Confidence | Why it fits |",
        "|---|---:|---:|---|",
    ]
    for cluster in top_clusters:
        lines.append(
            f"| {cluster['title']} | {cluster['total_score']:.2f} | {cluster['confidence']:.2f} | {', '.join(cluster['lineage_roots'][:2])} |"
        )

    for cluster in top_clusters:
        lines.extend(
            [
                "",
                f"## {cluster['title']}",
                "",
                f"- Profile fit score: `{cluster['profile_fit_score']:.2f}`",
                f"- Trend strength: `{cluster['trend_strength']:.2f}`",
                f"- Trend velocity: `{cluster['trend_velocity']:.2f}`",
                f"- Batch survival score: `{cluster['batch_survival_score']:.2f}`",
                f"- Adjacency score: `{cluster['adjacency_score']:.2f}`",
                f"- Question density: `{cluster['question_density']:.2f}`",
                f"- Surface spread: `{cluster['surface_spread']:.2f}`",
                f"- Context relevance: `{cluster['context_relevance']:.2f}`",
                "",
                "### Why it fits",
                f"- Connected roots: {', '.join(cluster['lineage_roots'])}",
                f"- Generations represented: {', '.join(str(value) for value in cluster['generations'])}",
                "",
                "### Trend behavior",
                f"- Representative terms: {', '.join(cluster['terms'][:6])}",
                "",
                "### Common question patterns",
            ]
        )
        if cluster["questions"]:
            lines.extend(f"- {question}" for question in cluster["questions"][:8])
        else:
            lines.append("- No strong question pattern surfaced from the active providers.")

        lines.extend(
            [
                "",
                "### Related terms/topics",
            ]
        )
        if cluster["related_terms"]:
            lines.extend(f"- {term}" for term in cluster["related_terms"][:10])
        else:
            lines.append("- No related-term signal was captured.")

        wedge = _suggest_wedge(cluster)
        lines.extend(
            [
                "",
                "### Possible wedge",
                f"- {wedge}",
                "",
                "### What this does not prove",
                "- It does not prove validated demand.",
                "- It does not prove low competition or willingness to pay.",
                "- It does not prove the cluster is unsaturated.",
                "",
                "### Next validation step",
                f"- Talk to 3 real operators who live near `{cluster['title']}` and test whether these question patterns map to active pain.",
            ]
        )

    lines.extend(["", "## Low-confidence or dropped clusters", ""])
    if dropped_clusters:
        for cluster in dropped_clusters[:8]:
            lines.append(
                f"- {cluster['title']}: dropped after ranking because score `{cluster['total_score']:.2f}` / confidence `{cluster['confidence']:.2f}` was weaker."
            )
    else:
        lines.append("- No dropped clusters in this run.")

    return "\n".join(lines) + "\n"


def _suggest_wedge(cluster: dict) -> str:
    title = cluster["title"]
    if cluster["questions"]:
        return f"Build a lightweight guide, workflow pack, or service around `{title}` that answers the top recurring questions first."
    return f"Explore a content-led or service-led wedge around `{title}` before building software."


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
