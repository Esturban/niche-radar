from __future__ import annotations

from .utils import clamp01, content_tokens, dedupe_preserve_order, normalize_search_term

NOISE_TOKENS = {
    "agency",
    "agencies",
    "certification",
    "certifications",
    "company",
    "companies",
    "course",
    "courses",
    "engineer",
    "engineers",
    "job",
    "jobs",
    "salary",
}
PACKAGING_TOKENS = {
    "consultant",
    "consultants",
    "service",
    "services",
    "software",
    "tool",
    "tools",
    "template",
    "templates",
}
AMBIGUOUS_SUPPORTING_TOKENS = {
    "analytics",
    "dashboard",
    "dashboards",
    "visualization",
    "visualizations",
}
GENERIC_PARENT_TOKENS = {
    "automation",
    "automations",
    "ecommerce",
    "operations",
    "operator",
    "operators",
    "shopify",
    "workflow",
    "workflows",
}
TRUSTED_WORKFLOW_TOKENS = {
    "alert",
    "alerts",
    "attribution",
    "exception",
    "exceptions",
    "forecast",
    "forecasting",
    "fulfillment",
    "fulfilment",
    "inventory",
    "lifecycle",
    "monitoring",
    "ops",
    "report",
    "reporting",
    "retention",
    "return",
    "returns",
}
WORKAROUND_TOKENS = {
    "cleanup",
    "copy",
    "copied",
    "copying",
    "csv",
    "export",
    "exports",
    "fire",
    "manual",
    "patch",
    "patching",
    "reconcile",
    "reconciliation",
    "sheet",
    "sheets",
    "spreadsheet",
    "spreadsheets",
}
TRUSTED_SIGNAL_CLASSES = {"trusted_workflow", "trusted_workaround"}
NON_TRUSTED_SIGNAL_CLASSES = {"supporting_artifact", "supporting_packaging", "noise"}


def classify_signal_text(text: str) -> str:
    tokens = set(content_tokens(normalize_search_term(text)))
    if not tokens:
        return "noise"
    if tokens & NOISE_TOKENS:
        return "noise"
    if tokens & WORKAROUND_TOKENS:
        return "trusted_workaround"
    if tokens & TRUSTED_WORKFLOW_TOKENS:
        return "trusted_workflow"
    if tokens & PACKAGING_TOKENS:
        return "supporting_packaging"
    if tokens & AMBIGUOUS_SUPPORTING_TOKENS:
        return "supporting_artifact"
    return "supporting_artifact"


def classify_evidence_snippet(snippet: str) -> str:
    return classify_signal_text(snippet)


def founder_core_tokens(text: str) -> list[str]:
    tokens = [
        token
        for token in content_tokens(normalize_search_term(text))
        if token not in NOISE_TOKENS and token not in PACKAGING_TOKENS and token not in GENERIC_PARENT_TOKENS
    ]
    return dedupe_preserve_order(tokens)


def is_packaging_heavy(text: str) -> bool:
    tokens = content_tokens(normalize_search_term(text))
    if not tokens:
        return True
    packaging = len([token for token in tokens if token in PACKAGING_TOKENS or token in AMBIGUOUS_SUPPORTING_TOKENS])
    if founder_core_tokens(text) and len(founder_core_tokens(text)) > 1:
        return (packaging / len(tokens)) >= 0.5
    return packaging > 0


def is_generic_parent_phrase(text: str) -> bool:
    core_tokens = founder_core_tokens(text)
    if core_tokens:
        return False
    tokens = set(content_tokens(normalize_search_term(text)))
    return bool(tokens) and tokens <= (GENERIC_PARENT_TOKENS | PACKAGING_TOKENS)


def summarize_signal_groups(*, terms: list[str], questions: list[str], related_terms: list[str]) -> dict:
    summary = {
        "trusted_terms": [],
        "trusted_questions": [],
        "trusted_related_terms": [],
        "supporting_terms": [],
        "supporting_questions": [],
        "supporting_related_terms": [],
        "packaging_terms": [],
        "noise_terms": [],
    }

    for source, values in (("term", terms), ("question", questions), ("related", related_terms)):
        for value in values:
            signal_class = classify_signal_text(value)
            if signal_class in TRUSTED_SIGNAL_CLASSES:
                summary[f"trusted_{'terms' if source == 'term' else 'questions' if source == 'question' else 'related_terms'}"].append(value)
            elif signal_class == "supporting_packaging":
                summary["packaging_terms"].append(value)
            elif signal_class == "noise":
                summary["noise_terms"].append(value)
            else:
                summary[f"supporting_{'terms' if source == 'term' else 'questions' if source == 'question' else 'related_terms'}"].append(value)

    trusted_total = (
        len(summary["trusted_terms"])
        + len(summary["trusted_questions"])
        + len(summary["trusted_related_terms"])
    )
    supporting_total = (
        len(summary["supporting_terms"])
        + len(summary["supporting_questions"])
        + len(summary["supporting_related_terms"])
    )
    total = max(
        1,
        trusted_total + supporting_total + len(summary["packaging_terms"]) + len(summary["noise_terms"]),
    )

    summary["trusted_signal_score"] = round(clamp01(trusted_total / 4), 4)
    summary["supporting_signal_score"] = round(clamp01(supporting_total / 6), 4)
    summary["packaging_penalty"] = round(clamp01(len(summary["packaging_terms"]) / total), 4)
    summary["noise_penalty"] = round(clamp01(len(summary["noise_terms"]) / total), 4)

    for key, value in list(summary.items()):
        if isinstance(value, list):
            summary[key] = dedupe_preserve_order(value)
    return summary
