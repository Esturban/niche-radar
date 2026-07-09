from __future__ import annotations

import csv
import json
from pathlib import Path

from .signal_quality import founder_core_tokens
from .utils import dedupe_preserve_order, normalize_search_term, now_iso

HEADLINE_PACKAGING_TOKENS = {
    "analytics",
    "consultant",
    "consultants",
    "dashboard",
    "dashboards",
    "software",
    "template",
    "templates",
    "tool",
    "tools",
    "visualization",
}


def write_outputs(
    outdir: Path,
    clusters: list[dict],
    all_terms: list[dict],
    question_graph: dict,
    evidence: list[dict],
    used_evidence: list[dict],
    provider_results: list[dict],
    run_meta: dict,
    top_niches: int,
    research_trace: dict,
    persist_trace: bool,
) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    top_clusters = clusters[:top_niches]
    dropped_clusters = clusters[top_niches:]

    (outdir / "report.md").write_text(render_report(top_clusters, dropped_clusters, run_meta), encoding="utf-8")
    (outdir / "clusters.json").write_text(json.dumps(top_clusters, indent=2), encoding="utf-8")
    (outdir / "used_evidence.json").write_text(json.dumps(used_evidence, indent=2), encoding="utf-8")
    (outdir / "run_meta.json").write_text(json.dumps(run_meta, indent=2), encoding="utf-8")

    if persist_trace:
        (outdir / "evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        (outdir / "question_graph.json").write_text(json.dumps(question_graph, indent=2), encoding="utf-8")
        (outdir / "provider_hits.json").write_text(json.dumps(provider_results, indent=2), encoding="utf-8")
        (outdir / "research_trace.json").write_text(json.dumps(research_trace, indent=2), encoding="utf-8")
        _write_terms_csv(outdir / "terms.csv", all_terms)
        _write_trends_csv(outdir / "trends.csv", all_terms)


def append_run_index(root: Path, record: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    with (root / "index.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"recorded_at": now_iso(), **record}) + "\n")


def render_report(top_clusters: list[dict], dropped_clusters: list[dict], run_meta: dict) -> str:
    focus = run_meta.get("focus") or "profile-driven"
    wedge_summary = run_meta.get("wedge_summary", {})
    focus_summary = run_meta.get("focus_summary", {})
    evidence_summary = run_meta.get("evidence_summary", {})
    recommendation_context = run_meta.get("recommendation_context", {})
    highlighted = _resolve_highlighted_cluster(top_clusters=top_clusters, run_meta=run_meta)
    source_labels = []
    if run_meta.get("resume_path"):
        source_labels.append(run_meta["resume_path"])
    if run_meta.get("site_url"):
        source_labels.append(run_meta["site_url"])

    near_misses = [cluster for cluster in top_clusters if cluster.get("cluster_id") != run_meta.get("recommended_cluster_id")]

    lines = [
        "# niche-radar report",
        "",
        "## Founder memo",
        "",
    ]

    if highlighted:
        lines.extend(_render_founder_memo(highlighted=highlighted, near_misses=near_misses, run_meta=run_meta))
    else:
        lines.extend(_render_no_call_memo(run_meta=run_meta))

    lines.extend(
        [
            "",
            "## Run context",
            f"- Focus bias: `{focus}`",
            f"- Profile sources: `{', '.join(source_labels) if source_labels else 'profile-driven'}`",
            f"- Policy version: `{run_meta.get('policy_version', 'n/a')}`",
            f"- Recommended call type: `{run_meta.get('recommended_call_type', 'winner')}`",
            f"- Founder readiness score: `{run_meta.get('founder_readiness_score', 0.0)}`",
            f"- Confidence floor: `{run_meta.get('confidence_floor', 0.0)}`",
            f"- Recommended bets found: `{wedge_summary.get('recommended_bet_count', 0)}`",
            f"- Specificity outcome: `{wedge_summary.get('specificity_outcome', 'unknown')}`",
            f"- Research depth: `{run_meta.get('research_summary', {}).get('depth', 'off')}`",
            f"- Focus gate threshold: `{focus_summary.get('threshold', 'n/a')}`",
            f"- Evidence gate: `{', '.join(evidence_summary.get('required_types', [])) or 'n/a'}`",
            f"- Highlighted recommendation: `{run_meta.get('recommended_cluster_title') or 'no-call'}`",
            "- External evidence is the backbone. Profile fit is a filter. False precision is a failure.",
            "",
            "### Founder context",
        ]
    )
    if recommendation_context.get("brief"):
        lines.append(f"- Founder brief: `{recommendation_context['brief']}`")
        if run_meta.get("brief_influence", {}).get("winner_changed"):
            lines.append("- Brief influence: `winner changed only after evidence, specificity, and profile-fit tie-breaks stayed close.`")
        else:
            lines.append("- Brief influence: `narrative/tie-break only; it did not overpower stronger evidence.`")
    else:
        lines.append("- Founder brief: `none provided`")

    lines.extend(
        [
            "",
            "## Appendix",
            "",
            "### Gate summary",
            f"- Focus-qualified clusters: `{len(focus_summary.get('accepted_clusters', []))}`",
            f"- Evidence-qualified clusters: `{len(evidence_summary.get('accepted_clusters', []))}`",
        ]
    )
    if focus_summary.get("rejected_clusters"):
        lines.append(
            "- Focus rejects: "
            + "; ".join(
                f"{item['cluster']} ({', '.join(item.get('reasons', [])) or 'rejected'})"
                for item in focus_summary["rejected_clusters"][:4]
            )
        )
    if evidence_summary.get("rejected_clusters"):
        lines.append(
            "- Evidence rejects: "
            + "; ".join(
                f"{item['cluster']} ({', '.join(item.get('reasons', [])) or 'rejected'})"
                for item in evidence_summary["rejected_clusters"][:4]
            )
        )

    lines.extend(
        [
            "",
            "### Ranked clusters",
            "",
            "| Cluster | Evidence | Specificity | Confidence | Citations |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for cluster in top_clusters:
        lines.append(
            f"| {cluster['title']} | {cluster['evidence_strength']:.2f} ({cluster['evidence_tier']}) | {cluster.get('specificity_score', 0.0):.2f} | {cluster['confidence']:.2f} | {cluster['citation_count']} |"
        )

    lines.extend(["", "### Cluster deep dives"])
    for cluster in top_clusters:
        lines.extend(_render_cluster_appendix(cluster=cluster, run_meta=run_meta))

    lines.extend(["", "### Lower-ranked niches"])
    if dropped_clusters:
        for cluster in dropped_clusters[:8]:
            lines.append(
                f"- {cluster['title']}: lower-ranked because evidence `{cluster['evidence_strength']:.2f}` / confidence `{cluster['confidence']:.2f}` / specificity `{cluster.get('specificity_score', 0.0):.2f}` was weaker."
            )
    else:
        lines.append("- No dropped clusters in this run.")

    return "\n".join(lines) + "\n"


def render_insufficient_signal_report(*, focus: str, seeds: list[str], reasons: list[str], brief: str) -> str:
    recommendation_context = {"brief": brief.strip()}
    lines = [
        "# niche-radar report",
        "",
        "## Founder memo",
        "",
        "### Recommended niche",
        "- No call. This run did not surface a niche I would trust enough to test yet.",
        "",
        "### Who has this problem",
        f"- The current focus was `{focus or 'profile-driven'}`, but the live signal was too thin to narrow confidently.",
        "",
        "### Painful workflow",
        "- The tool could not verify a recurring workflow strongly enough to turn it into a founder recommendation.",
        "",
        "### Why this is worth pausing on",
        "- A weak signal should slow the founder down, not push them into fake conviction.",
        "- The right move here is a no-call, not a hollow wedge.",
        "",
        "### What evidence keeps showing up",
        "- Not enough live provider signal came back to rank clusters honestly.",
        *[f"- Provider issue: {reason}" for reason in reasons if reason][:4],
        "",
        "### Why there is no winner yet",
        "- The run never cleared the evidence bar needed for a recommendation memo.",
        "- Forcing a winner here would make the founder do the trust work manually anyway.",
        "",
        "### What this does not prove",
        "- It does not prove there is no opportunity here.",
        "- It does prove this run did not gather enough evidence to narrow honestly.",
        "",
        "### Next 3 validation conversations/tests",
        "1. Target: people closest to the focus area you entered.",
        "   Hypothesis: there is a recurring workflow problem here, but the current providers did not surface it clearly.",
        "   Prompt: walk me through the last time this workflow broke, dragged, or required manual cleanup.",
        "2. Target: operators already searching for templates, tutorials, or exports around this area.",
        "   Hypothesis: if the pain is real, people are already patching it with ad hoc workarounds.",
        "   Prompt: what spreadsheet, dashboard, template, or workaround are you relying on today?",
        "3. Target: adjacent operators one layer outside the exact focus.",
        "   Hypothesis: the problem may be real, but the current wording of the niche is too broad or too off-target.",
        "   Prompt: if you had to rename this workflow in your own words, what would you call it?",
        "",
        "## Run context",
        f"- Focus bias: `{focus or 'profile-driven'}`",
        f"- Founder brief: `{recommendation_context['brief'] or 'none provided'}`",
        "",
        "## Seed terms attempted",
        *[f"- {seed}" for seed in seeds],
    ]
    return "\n".join(lines) + "\n"


def _render_founder_memo(*, highlighted: dict, near_misses: list[dict], run_meta: dict) -> list[str]:
    niche_statement = _founder_niche_statement(highlighted=highlighted, run_meta=run_meta)
    icp = _infer_icp(highlighted=highlighted, run_meta=run_meta)
    workflow = _workflow_phrase(highlighted=highlighted)
    worthwhile = _worthwhile_bullets(highlighted=highlighted)
    evidence_lines = _evidence_signal_lines(highlighted=highlighted)
    validation_plan = _validation_plan(highlighted=highlighted)

    lines = [
        "### Recommended niche",
        f"- {niche_statement}",
        f"- Working wedge from this run: `{_working_wedge_label(highlighted)}`",
        "",
        "### Who has this problem",
        f"- {icp}",
        "",
        "### Painful workflow",
        f"- {workflow}",
        "",
        "### Why this is worth testing",
    ]
    lines.extend(f"- {item}" for item in worthwhile)
    lines.extend(["", "### What evidence keeps showing up"])
    lines.extend(f"- {item}" for item in evidence_lines)
    lines.extend(["", "### Why this won over the near-misses"])
    if near_misses:
        for cluster in near_misses[:3]:
            lines.append(f"- {_near_miss_line(winner=highlighted, cluster=cluster)}")
    else:
        lines.append("- No serious near-miss showed up inside the top-ranked set.")

    lines.extend(
        [
            "",
            "### What this does not prove",
            "- It does not prove validated demand.",
            "- It does not prove low competition or willingness to pay.",
            "- It does not prove the niche is unsaturated.",
            "",
            "### Next 3 validation conversations/tests",
        ]
    )
    for index, plan in enumerate(validation_plan, start=1):
        lines.extend(
            [
                f"{index}. Target: {plan['target']}",
                f"   Hypothesis: {plan['hypothesis']}",
                f"   Prompt: {plan['prompt']}",
            ]
        )
    return lines


def _render_no_call_memo(*, run_meta: dict) -> list[str]:
    focus = run_meta.get("focus") or "profile-driven"
    accepted_focus = len(run_meta.get("focus_summary", {}).get("accepted_clusters", []))
    accepted_evidence = len(run_meta.get("evidence_summary", {}).get("accepted_clusters", []))
    return [
        "### Recommended niche",
        "- No call. None of the candidate niches earned a founder-quality recommendation honestly.",
        "",
        "### Who has this problem",
        f"- The run stayed centered on `{focus}`, but the evidence stayed too weak or too muddy to narrow safely.",
        "",
        "### Painful workflow",
        "- The current artifact set does not isolate a recurring painful workflow tightly enough yet.",
        "",
        "### Why this is worth pausing on",
        "- A no-call is useful here. It prevents fake conviction.",
        f"- Focus-qualified clusters: `{accepted_focus}`. Evidence-qualified clusters: `{accepted_evidence}`.",
        "",
        "### What evidence keeps showing up",
        "- The pipeline found adjacent terms and candidates, but not a winner strong enough to trust.",
        "- That usually means the niche wording is still broad, the live signal is thin, or the evidence is pointing in multiple directions.",
        "",
        "### Why there is no winner yet",
        "- The report is refusing to turn weak evidence into founder advice.",
        "",
        "### What this does not prove",
        "- It does not prove there is no opportunity here.",
        "- It does prove the current run should not be treated like a decision memo yet.",
        "",
        "### Next 3 validation conversations/tests",
        "1. Target: operators closest to the focus you entered.",
        "   Hypothesis: there is a real workflow pain here, but the wording is still too broad.",
        "   Prompt: if you had to describe the most annoying recurring workflow in this area, what would you call it?",
        "2. Target: people already using templates, exports, or dashboards around this focus.",
        "   Hypothesis: repeated workaround behavior will expose a tighter wedge than the raw focus term.",
        "   Prompt: what are you exporting, copying, or patching manually every week?",
        "3. Target: the top adjacent niche that almost surfaced from this run.",
        "   Hypothesis: one of the near-misses may become the real wedge once you tighten the language.",
        "   Prompt: walk me through the last time this adjacent workflow caused delay, cleanup, or a fire drill.",
    ]


def _render_cluster_appendix(*, cluster: dict, run_meta: dict) -> list[str]:
    wedge = _cluster_wedge(cluster)
    default_next_action = (
        f"Talk to 3 operators around `{wedge.get('label', cluster['title'])}` and test whether the cited problems map to active pain worth paying to fix."
    )

    lines = [
        "",
        f"#### {cluster['title']}",
        "",
        f"- Evidence tier: `{cluster['evidence_tier']}`",
        f"- Evidence strength: `{cluster['evidence_strength']:.2f}`",
        f"- Citation count: `{cluster['citation_count']}`",
        f"- Surface count: `{cluster['surface_count']}`",
        f"- Profile fit score: `{cluster['profile_fit_score']:.2f}`",
        f"- Trend strength: `{cluster['trend_strength']:.2f}`",
        f"- Recency support: `{cluster['recency_support']:.2f}`",
        f"- Specificity score: `{cluster.get('specificity_score', 0.0):.2f}`",
        f"- Focus score: `{cluster.get('focus_score', 0.0):.2f}`",
        f"- Focus gate: `{cluster.get('focus_gate', False)}`",
        f"- Evidence gate: `{cluster.get('evidence_gate', False)}`",
        f"- Brief alignment score: `{cluster.get('brief_alignment_score', 0.0):.2f}`",
        f"- Evidence types: `{', '.join(cluster.get('evidence_types', [])) or 'none'}`",
        f"- Trusted signal score: `{cluster.get('trusted_signal_score', 0.0):.2f}`",
        f"- Supporting signal score: `{cluster.get('supporting_signal_score', 0.0):.2f}`",
        f"- Noise penalty: `{cluster.get('noise_penalty', 0.0):.2f}`",
        f"- Packaging penalty: `{cluster.get('packaging_penalty', 0.0):.2f}`",
        f"- Founder readiness score: `{cluster.get('founder_readiness_score', 0.0):.2f}`",
        f"- Founder recommendable: `{cluster.get('founder_recommendable', False)}`",
        f"- Confidence: `{cluster['confidence']:.2f}`",
        f"- Research score: `{cluster.get('research_score', 0.0):.2f}`",
        "",
        "##### Why it fits",
        f"- Connected roots: {', '.join(cluster['lineage_roots'])}",
        f"- Generations represented: {', '.join(str(value) for value in cluster['generations'])}",
        f"- Recommendation status: `{_recommendation_status(cluster=cluster, run_meta=run_meta)}`",
        "",
        "##### Dossier verdict",
        f"- Verdict: `{cluster.get('dossier', {}).get('verdict', 'n/a')}`",
        f"- Why non-obvious: {cluster.get('dossier', {}).get('why_non_obvious', 'No dossier summary generated.')}",
        f"- Demand summary: {cluster.get('dossier', {}).get('demand_summary', 'No dossier summary generated.')}",
        f"- Search summary: {cluster.get('dossier', {}).get('search_summary', 'No dossier summary generated.')}",
        f"- Risk summary: {cluster.get('dossier', {}).get('risk_summary', 'No dossier summary generated.')}",
        "",
        "##### Why it surfaced externally",
        f"- Representative terms: {', '.join(cluster['terms'][:6])}",
        f"- Recurring related terms: {', '.join(cluster['related_terms'][:6]) if cluster['related_terms'] else 'No strong related-term signal captured.'}",
        "",
        "##### Common question patterns",
    ]

    if cluster["questions"]:
        lines.extend(f"- {question}" for question in cluster["questions"][:8])
    else:
        lines.append("- No strong question pattern surfaced from the active providers.")

    lines.extend(["", "##### Supporting evidence"])
    evidence_items = cluster.get("used_evidence") or cluster.get("evidence", [])
    if evidence_items:
        for item in evidence_items[:5]:
            lines.append(f"- [{item['title']}]({item['url']}): {item['snippet']}")
    else:
        lines.append("- No public evidence pages were captured for this niche in this run.")

    lines.extend(["", "##### Gate failures"])
    if cluster.get("recommendation_failure_reasons") or cluster.get("founder_rejection_reasons"):
        lines.extend(f"- {reason}" for reason in cluster.get("recommendation_failure_reasons", []))
        lines.extend(f"- {reason}" for reason in cluster.get("founder_rejection_reasons", []))
    else:
        lines.append("- None. This cluster cleared the recommendation gates.")

    lines.extend(
        [
            "",
            "##### Suggested wedge",
            f"- {cluster['suggested_wedge']}",
            "",
            "##### Micro-wedge judgment",
            f"- Label: `{wedge.get('label', cluster['title'])}`",
            f"- Rejection reason: `{wedge.get('rejection_reason', 'accepted')}`" if wedge.get("rejection_reason") else "- Rejection reason: `accepted`",
            f"- Advice: {wedge.get('advice', cluster['advice'])}",
            "",
            "##### Wedge support",
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
            "##### What this does not prove",
            "- It does not prove validated demand.",
            "- It does not prove low competition or willingness to pay.",
            "- It does not prove the cluster is unsaturated.",
            "",
            "##### Next validation step",
            f"- {cluster.get('dossier', {}).get('next_action', default_next_action)}",
        ]
    )
    return lines


def _cluster_wedge(cluster: dict) -> dict:
    return cluster.get("recommended_wedge") or ((cluster.get("micro_wedges") or [None])[0] or {})


def _resolve_highlighted_cluster(*, top_clusters: list[dict], run_meta: dict) -> dict | None:
    highlighted_id = run_meta.get("recommended_cluster_id")
    if highlighted_id:
        return next((cluster for cluster in top_clusters if cluster.get("cluster_id") == highlighted_id), None)
    return None


def _recommendation_status(*, cluster: dict, run_meta: dict) -> str:
    if cluster.get("cluster_id") == run_meta.get("recommended_cluster_id"):
        return "highlighted"
    if cluster.get("recommended_bet"):
        return "gate-passed"
    return "rejected"


def _working_wedge_label(cluster: dict) -> str:
    wedge = _cluster_wedge(cluster)
    return wedge.get("label") or cluster.get("title") or cluster.get("title_seed", "n/a")


def _founder_niche_statement(*, highlighted: dict, run_meta: dict) -> str:
    icp = _infer_icp(highlighted=highlighted, run_meta=run_meta)
    workflow = _workflow_phrase(highlighted=highlighted)
    return f"{icp} dealing with {workflow}."


def _infer_icp(*, highlighted: dict, run_meta: dict) -> str:
    corpus = " ".join(
        [
            run_meta.get("focus", ""),
            highlighted.get("title", ""),
            highlighted.get("title_seed", ""),
            _working_wedge_label(highlighted),
            " ".join(highlighted.get("terms", [])[:6]),
            " ".join(highlighted.get("related_terms", [])[:6]),
        ]
    ).lower()

    if "small business" in corpus:
        return "Small-business owners and operators"
    if "merchant" in corpus and "shopify" in corpus:
        return "Shopify merchants and operators"
    if "operator" in corpus and "shopify" in corpus:
        return "Shopify operators"
    if "shopify" in corpus:
        return "Shopify operators and merchant leads"
    if "operator" in corpus:
        return "Operators closest to this workflow"
    return "People closest to this workflow"


def _workflow_phrase(*, highlighted: dict) -> str:
    wedge = _cluster_wedge(highlighted)
    candidates = [
        wedge.get("workflow_or_pain", ""),
        *highlighted.get("trusted_questions", [])[:4],
        *highlighted.get("trusted_related_terms", [])[:4],
        *highlighted.get("trusted_terms", [])[:4],
        highlighted.get("title_seed", ""),
    ]
    for candidate in candidates:
        phrase = _workflow_phrase_from_candidate(candidate)
        if phrase:
            return phrase
    return "a recurring manual workflow that teams are still patching with tutorials, templates, and ad hoc tools"


def _workflow_phrase_from_candidate(candidate: str) -> str | None:
    normalized = normalize_search_term(candidate)
    if not normalized:
        return None
    if "report" in normalized:
        return "manual reporting, recurring exports, and ops review prep"
    if "dashboard" in normalized:
        return "manual KPI visibility, exception tracking, and dashboard upkeep"
    if "analytic" in normalized:
        return "manual analysis before ops decisions get made"
    if "visualization" in normalized or "visualisation" in normalized:
        return "manual KPI visibility work and status-sharing across the team"
    if "workflow" in normalized and "automation" in normalized:
        return "repeated workflows people are still trying to automate in pieces"
    if "operations automation" in normalized or ("operations" in normalized and "automation" in normalized):
        return "repeated operations work that teams are still patching by hand"

    tokens = [token for token in founder_core_tokens(normalized) if token not in HEADLINE_PACKAGING_TOKENS]
    if {"operations", "automation"} <= set(tokens):
        return "repeated operations work that teams are still patching by hand"
    if tokens:
        return f"manual {' '.join(tokens[:4])} work that still needs cleanup every week"
    return None


def _worthwhile_bullets(*, highlighted: dict) -> list[str]:
    questions = highlighted.get("trusted_questions", [])[:3]
    related = highlighted.get("trusted_related_terms", [])[:3]
    evidence_titles = [item.get("title", "") for item in _trusted_evidence_items(highlighted)[:3]]

    bullets = []
    if questions:
        bullets.append(
            "People keep phrasing this like an active problem, not a theory, with recurring searches such as "
            + ", ".join(f"`{question}`" for question in questions)
            + "."
        )
    if related:
        bullets.append(
            "Workaround behavior keeps surfacing through manual patch-job patterns like "
            + ", ".join(f"`{term}`" for term in related)
            + "."
        )
    if evidence_titles:
        bullets.append(
            "Distinct evidence pages keep pointing at the same workflow, including "
            + ", ".join(f"`{title}`" for title in evidence_titles)
            + "."
        )
    bullets.append(
        f"It kept both evidence strength `{highlighted.get('evidence_strength', 0.0):.2f}` and specificity `{highlighted.get('specificity_score', 0.0):.2f}`, which is the combination you want before spending founder time."
    )
    return dedupe_preserve_order(bullets)[:4]


def _evidence_signal_lines(*, highlighted: dict) -> list[str]:
    questions = highlighted.get("trusted_questions", [])[:4]
    related = highlighted.get("trusted_related_terms", [])[:4]
    evidence_items = _trusted_evidence_items(highlighted)

    lines = []
    if questions:
        lines.append("Repeated question patterns: " + ", ".join(f"`{item}`" for item in questions) + ".")
    if related:
        lines.append("Repeated workaround or learning signals: " + ", ".join(f"`{item}`" for item in related) + ".")
    if evidence_items:
        refs = [f"[{item['title']}]({item['url']})" for item in evidence_items[:3]]
        lines.append("Supporting evidence pages: " + ", ".join(refs) + ".")
    if not lines:
        lines.append("The cluster stayed alive through both search-adjacent signals and public evidence pages, even when the wording varied.")
    return lines[:4]


def _near_miss_line(*, winner: dict, cluster: dict) -> str:
    wedge = _cluster_wedge(cluster)
    label = wedge.get("label", cluster.get("title", "near miss"))
    if cluster.get("founder_rejection_reasons"):
        return f"`{label}` lost because {cluster['founder_rejection_reasons'][0]}."
    if cluster.get("recommendation_failure_reasons"):
        return f"`{label}` lost because {cluster['recommendation_failure_reasons'][0]}."

    winner_evidence = float(winner.get("evidence_strength", 0.0))
    cluster_evidence = float(cluster.get("evidence_strength", 0.0))
    winner_specificity = float(winner.get("specificity_score", 0.0))
    cluster_specificity = float(cluster.get("specificity_score", 0.0))
    winner_fit = float(winner.get("profile_fit_score", 0.0))
    cluster_fit = float(cluster.get("profile_fit_score", 0.0))
    winner_readiness = float(winner.get("founder_readiness_score", 0.0))
    cluster_readiness = float(cluster.get("founder_readiness_score", 0.0))

    if cluster_readiness + 0.05 < winner_readiness:
        return f"`{label}` had signal, but the winner translated into a sharper founder-ready wedge."
    if cluster_evidence + 0.03 < winner_evidence:
        return f"`{label}` stayed plausible, but the winner kept stronger evidence `{winner_evidence:.2f}` vs `{cluster_evidence:.2f}`."
    if cluster_specificity + 0.03 < winner_specificity:
        return f"`{label}` had signal, but it stayed broader and less testable than the winner."
    if cluster_fit + 0.03 < winner_fit:
        return f"`{label}` lived in the same space, but it matched your background less cleanly."
    return f"`{label}` was close, but the winner had the cleaner mix of evidence, specificity, and founder usefulness."


def _validation_plan(*, highlighted: dict) -> list[dict]:
    icp = _infer_icp(highlighted=highlighted, run_meta={})
    workflow = _workflow_phrase(highlighted=highlighted)
    questions = highlighted.get("trusted_questions", [])[:3]
    related = highlighted.get("trusted_related_terms", [])[:3]
    working_wedge = _working_wedge_label(highlighted)
    signal_term = questions[0] if questions else (related[0] if related else working_wedge)
    clean_signal = _clean_founder_phrase(signal_term) or working_wedge

    return [
        {
            "target": f"{icp} currently doing {workflow}.",
            "hypothesis": "They are still running this workflow manually every week because the existing setup does not cover the messy edge cases.",
            "prompt": f"Walk me through the last time you had to handle {workflow} by hand.",
        },
        {
            "target": f"{icp} already relying on spreadsheets, exports, or ad hoc workarounds around `{clean_signal}`.",
            "hypothesis": "Repeated workaround behavior usually means the pain is real, but the market still lacks a clean default workflow.",
            "prompt": "What spreadsheet, export, or manual workaround are you relying on today, and where does it break?",
        },
        {
            "target": f"{icp} evaluating whether to buy, build, or ignore a fix for `{working_wedge}`.",
            "hypothesis": "If the pain is real, there is a narrow first wedge that saves time before you ever pitch a bigger platform story.",
            "prompt": "If this workflow got 80 percent easier next week, what meeting, report, or fire drill would change first?",
        },
    ]


def _trusted_evidence_items(highlighted: dict) -> list[dict]:
    evidence_items = highlighted.get("used_evidence") or highlighted.get("evidence", [])
    trusted = [item for item in evidence_items if item.get("signal_class") in {"trusted_workflow", "trusted_workaround"}]
    return trusted or evidence_items


def _clean_founder_phrase(value: str) -> str:
    tokens = founder_core_tokens(value)
    if tokens:
        return " ".join(tokens[:5])
    return normalize_search_term(value).strip()


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
