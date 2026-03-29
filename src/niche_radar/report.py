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
    wedge_summary = run_meta.get("wedge_summary", {})
    source_labels = []
    if run_meta.get("resume_path"):
        source_labels.append(run_meta["resume_path"])
    if run_meta.get("site_url"):
        source_labels.append(run_meta["site_url"])

    recommended = [cluster for cluster in top_clusters if cluster.get("recommended_bet")][:2]
    near_misses = [cluster for cluster in top_clusters if not cluster.get("recommended_bet")]

    lines = [
        "# niche-radar report",
        "",
        "## Executive summary",
        f"- Focus bias: `{focus}`",
        f"- Profile sources: `{', '.join(source_labels) if source_labels else 'profile-driven'}`",
        f"- Confidence floor: `{run_meta['confidence_floor']}`",
        f"- Recommended bets found: `{wedge_summary.get('recommended_bet_count', 0)}`",
        f"- Specificity outcome: `{wedge_summary.get('specificity_outcome', 'unknown')}`",
        "- This report tries to cut broad discovery down to 1-2 evidence-backed bets.",
        "- External evidence is the backbone. Profile fit is a filter. False precision is a failure.",
        "- It does not validate market demand, willingness to pay, or lack of saturation.",
        "",
        "## Recommended bets",
        "",
    ]
    if recommended:
        lines.extend(
            [
                "| Bet | Evidence | Specificity | Confidence |",
                "|---|---:|---:|---:|",
            ]
        )
        for cluster in recommended:
            wedge = cluster.get("recommended_wedge") or {}
            lines.append(
                f"| {wedge.get('label', cluster['title'])} | {cluster['evidence_strength']:.2f} ({cluster['evidence_tier']}) | {cluster.get('specificity_score', 0.0):.2f} | {cluster['confidence']:.2f} |"
            )
    else:
        lines.extend(
            [
                "- No cluster reached the specificity bar for an evidence-backed founder-style recommendation.",
                "- The current run surfaced broad territory, but not a narrow enough bet to advise on honestly.",
            ]
        )

    lines.extend(["", "## Near misses", ""])
    if near_misses:
        for cluster in near_misses[:4]:
            wedge = (cluster.get("micro_wedges") or [{}])[0]
            lines.append(
                f"- {wedge.get('label', cluster['title'])}: `{wedge.get('rejection_reason', cluster.get('rejection_reason', 'not specific enough'))}`."
            )
    else:
        lines.append("- No near misses in this run.")

    lines.extend(
        [
            "",
            "## Ranked clusters",
            "",
            "| Cluster | Evidence | Specificity | Confidence | Citations |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for cluster in top_clusters:
        lines.append(
            f"| {cluster['title']} | {cluster['evidence_strength']:.2f} ({cluster['evidence_tier']}) | {cluster.get('specificity_score', 0.0):.2f} | {cluster['confidence']:.2f} | {cluster['citation_count']} |"
        )

    for cluster in top_clusters:
        wedge = cluster.get("recommended_wedge") or ((cluster.get("micro_wedges") or [None])[0] or {})
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
                f"- Specificity score: `{cluster.get('specificity_score', 0.0):.2f}`",
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
                "### Micro-wedge judgment",
                f"- Label: `{wedge.get('label', cluster['title'])}`",
                f"- Rejection reason: `{wedge.get('rejection_reason', 'accepted')}`" if wedge.get("rejection_reason") else "- Rejection reason: `accepted`",
                f"- Advice: {wedge.get('advice', cluster['advice'])}",
                "",
                "### Wedge support",
            ]
        )
        if wedge.get("supporting_terms"):
            lines.append(f"- Supporting terms: {', '.join(wedge['supporting_terms'][:4])}")
        else:
            lines.append("- Supporting terms: No strong narrowing terms surfaced.")
        if wedge.get("supporting_questions"):
            lines.append(f"- Supporting questions: {', '.join(wedge['supporting_questions'][:4])}")
        else:
            lines.append("- Supporting questions: No strong narrowing questions surfaced.")
        if wedge.get("evidence_refs"):
            evidence_labels = [f"[{item['title']}]({item['url']})" for item in wedge["evidence_refs"][:3]]
            lines.append(f"- Evidence refs: {', '.join(evidence_labels)}")
        else:
            lines.append("- Evidence refs: No evidence items strongly supported this narrower wedge.")

        lines.extend(
            [
                "",
                "### What this does not prove",
                "- It does not prove validated demand.",
                "- It does not prove low competition or willingness to pay.",
                "- It does not prove the cluster is unsaturated.",
                "",
                "### Next validation step",
                f"- Talk to 3 operators around `{wedge.get('label', cluster['title'])}` and test whether the cited problems map to active pain worth paying to fix.",
            ]
        )

    lines.extend(["", "## Lower-ranked niches", ""])
    if dropped_clusters:
        for cluster in dropped_clusters[:8]:
            lines.append(
                f"- {cluster['title']}: lower-ranked because evidence `{cluster['evidence_strength']:.2f}` / confidence `{cluster['confidence']:.2f}` / specificity `{cluster.get('specificity_score', 0.0):.2f}` was weaker."
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
