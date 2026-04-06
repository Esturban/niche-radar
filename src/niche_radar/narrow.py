from __future__ import annotations

import re

from .signal_quality import (
    GENERIC_PARENT_TOKENS,
    PACKAGING_TOKENS,
    TRUSTED_SIGNAL_CLASSES,
    classify_signal_text,
    founder_core_tokens,
    is_generic_parent_phrase,
    is_packaging_heavy,
)
from .utils import INTENT_MARKERS, clamp01, content_tokens, normalize_search_term, shared_token_score

MAX_WEDGES_PER_CLUSTER = 2
MIN_SPECIFICITY_SCORE = 0.58
CONTEXT_FALLBACK = "small businesses"
CONTEXT_STOPWORDS = {
    "business",
    "businesses",
    "owner",
    "owners",
    "operator",
    "operators",
    "smb",
    "smbs",
    "small",
    "team",
    "teams",
}
WORKFLOW_STOPWORDS = CONTEXT_STOPWORDS | set(INTENT_MARKERS) | {"ideas", "reddit"} | GENERIC_PARENT_TOKENS | PACKAGING_TOKENS
OFFER_MAP = {
    "consultant": "service offer",
    "service": "service offer",
    "services": "service offer",
    "software": "lightweight tool",
    "tool": "lightweight tool",
    "tools": "lightweight tool",
    "template": "workflow pack",
}
CONTEXT_PATTERNS = [
    (re.compile(r"\bowner-led smb[s]?\b"), "owner-led SMBs"),
    (re.compile(r"\bowner-led small businesses?\b"), "owner-led small businesses"),
    (re.compile(r"\bservice businesses?\b"), "service businesses"),
    (re.compile(r"\boperations teams?\b"), "operations teams"),
    (re.compile(r"\bsmall businesses?\b"), "small businesses"),
    (re.compile(r"\bsmall business\b"), "small businesses"),
]


def attach_micro_wedges(clusters: list[dict], evidence_by_cluster: dict[str, dict]) -> list[dict]:
    enriched: list[dict] = []
    for cluster in clusters:
        evidence_items = evidence_by_cluster.get(cluster["cluster_id"], {}).get("items", [])
        micro_wedges = _derive_micro_wedges(cluster=cluster, evidence_items=evidence_items)
        accepted = next((item for item in micro_wedges if not item.get("rejection_reason")), None)
        best_candidate = micro_wedges[0] if micro_wedges else None
        enriched.append(
            {
                **cluster,
                "micro_wedges": micro_wedges,
                "recommended_wedge": accepted,
                "recommended_bet": accepted is not None,
                "specificity_score": round((accepted or best_candidate or {}).get("specificity_score", 0.0), 4),
                "rejection_reason": None if accepted else (best_candidate or {}).get("rejection_reason", "not specific enough"),
                "advice": (accepted or best_candidate or {}).get("advice", "Not specific enough to advise on honestly."),
            }
        )
    return enriched


def _derive_micro_wedges(cluster: dict, evidence_items: list[dict]) -> list[dict]:
    title = cluster["title_seed"]
    title_similarity_base = title.replace("small business", "").strip() or title
    candidates: dict[str, dict] = {}

    for source_kind, text in _source_texts(cluster):
        normalized = normalize_search_term(text)
        tokens = content_tokens(normalized)
        if len(tokens) < 2 or len(tokens) > 8:
            continue
        workflow = _extract_workflow_or_pain(normalized, fallback=title_similarity_base)
        if not workflow:
            continue
        context = _extract_target_context(normalized, title)
        offer = _derive_offer(normalized)
        label = _build_label(workflow, context)
        key = f"{label}|{offer}"
        entry = candidates.setdefault(
            key,
            {
                "label": label,
                "workflow_or_pain": workflow,
                "target_context": context,
                "suggested_offer": offer,
                "supporting_terms": [],
                "supporting_questions": [],
                "trusted_support": [],
                "source_kinds": set(),
                "raw_support": [],
            },
        )
        entry["source_kinds"].add(source_kind)
        entry["raw_support"].append(normalized)
        if source_kind == "question":
            entry["supporting_questions"].append(normalized)
        else:
            entry["supporting_terms"].append(normalized)
        if source_kind == "question" and normalized in cluster.get("trusted_questions", []):
            entry["trusted_support"].append(normalized)
        elif source_kind == "related" and normalized in cluster.get("trusted_related_terms", []):
            entry["trusted_support"].append(normalized)
        elif source_kind in {"root", "term"} and normalized in cluster.get("trusted_terms", []):
            entry["trusted_support"].append(normalized)
        elif classify_signal_text(normalized) in TRUSTED_SIGNAL_CLASSES:
            entry["trusted_support"].append(normalized)

    if not candidates:
        return [_placeholder_candidate(cluster)]

    cluster_tokens = set(content_tokens(title))
    scored = []
    for entry in candidates.values():
        scored.append(_score_candidate(entry=entry, cluster=cluster, cluster_tokens=cluster_tokens, evidence_items=evidence_items))

    ranked = sorted(
        scored,
        key=lambda item: (
            not bool(item.get("rejection_reason")),
            item["specificity_score"],
            len(item["evidence_refs"]),
            len(item["source_kinds"]),
        ),
        reverse=True,
    )
    return ranked[:MAX_WEDGES_PER_CLUSTER]


def _score_candidate(entry: dict, cluster: dict, cluster_tokens: set[str], evidence_items: list[dict]) -> dict:
    label = entry["label"]
    label_tokens = set(content_tokens(label))
    raw_support = entry["raw_support"]
    raw_support_count = len(raw_support)
    extra_detail = len([token for token in label_tokens if token not in cluster_tokens])
    detail_score = min(1.0, extra_detail / 3)
    intent_score = 1.0 if entry["suggested_offer"] != "workflow pack" or any(marker in " ".join(raw_support) for marker in INTENT_MARKERS) else 0.4
    source_diversity = len(entry["source_kinds"]) / 4
    repetition_score = min(1.0, raw_support_count / 3)
    evidence_refs = _match_evidence(label_tokens=label_tokens, workflow=entry["workflow_or_pain"], evidence_items=evidence_items)
    trusted_evidence_refs = [item for item in evidence_refs if item.get("signal_class") in TRUSTED_SIGNAL_CLASSES]
    evidence_support = min(1.0, len(evidence_refs) / 2)
    lexical_penalty = 0.22 if shared_token_score(label, cluster["title_seed"]) >= 0.85 and extra_detail <= 1 else 0.0
    evidence_penalty = 0.28 if not evidence_refs else 0.0
    packaging_penalty = 0.28 if is_packaging_heavy(label) else 0.0
    generic_penalty = 0.30 if is_generic_parent_phrase(label) or is_generic_parent_phrase(entry["workflow_or_pain"]) else 0.0
    trusted_support = min(1.0, len(entry["trusted_support"]) / 2)

    specificity_score = clamp01(
        source_diversity * 0.22
        + repetition_score * 0.14
        + intent_score * 0.14
        + detail_score * 0.18
        + evidence_support * 0.32
        - lexical_penalty
        - evidence_penalty
        - packaging_penalty
        - generic_penalty
    )

    rejection_reasons: list[str] = []
    if not evidence_refs:
        rejection_reasons.append("weak evidence")
    if not trusted_evidence_refs:
        rejection_reasons.append("weak trusted evidence")
    if not founder_core_tokens(entry["workflow_or_pain"]):
        rejection_reasons.append("missing concrete workflow")
    if packaging_penalty > 0:
        rejection_reasons.append("packaging-heavy")
    if generic_penalty > 0 or lexical_penalty > 0:
        rejection_reasons.append("too broad")
    if trusted_support == 0.0:
        rejection_reasons.append("missing trusted signal")
    if specificity_score < MIN_SPECIFICITY_SCORE:
        rejection_reasons.append("low specificity")
    rejection_reason = rejection_reasons[0] if rejection_reasons else None

    advice = _build_advice(
        label=label,
        offer=entry["suggested_offer"],
        supporting_terms=entry["supporting_terms"],
        rejection_reason=rejection_reason,
    )

    return {
        "label": label,
        "workflow_or_pain": entry["workflow_or_pain"],
        "supporting_terms": entry["supporting_terms"][:4],
        "supporting_questions": entry["supporting_questions"][:4],
        "evidence_refs": evidence_refs,
        "trusted_evidence_refs": trusted_evidence_refs,
        "trusted_support": entry["trusted_support"][:4],
        "specificity_score": round(specificity_score, 4),
        "advice": advice,
        "rejection_reason": rejection_reason,
        "founder_rejection_reasons": rejection_reasons,
        "founder_ready": not rejection_reasons,
        "packaging_penalty": round(packaging_penalty, 4),
        "generic_penalty": round(generic_penalty, 4),
        "source_kinds": sorted(entry["source_kinds"]),
    }


def _match_evidence(label_tokens: set[str], workflow: str, evidence_items: list[dict]) -> list[dict]:
    matches: list[dict] = []
    workflow_tokens = set(content_tokens(workflow))
    for item in evidence_items:
        evidence_text = " ".join(
            [
                item.get("title", ""),
                item.get("snippet", ""),
                " ".join(item.get("matched_terms", [])),
            ]
        ).lower()
        overlap = len(set(content_tokens(evidence_text)) & (label_tokens | workflow_tokens))
        if overlap < 2:
            continue
        matches.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "signal_class": item.get("signal_class")
                or classify_signal_text(f"{item.get('title', '')} {item.get('snippet', '')}"),
            }
        )
        if len(matches) >= 3:
            break
    return matches


def _source_texts(cluster: dict) -> list[tuple[str, str]]:
    output: list[tuple[str, str]] = []
    trusted_terms = cluster.get("trusted_terms") or cluster.get("terms", [])
    trusted_related_terms = cluster.get("trusted_related_terms") or cluster.get("related_terms", [])
    trusted_questions = cluster.get("trusted_questions") or cluster.get("questions", [])
    supporting_related_terms = cluster.get("supporting_related_terms") or cluster.get("related_terms", [])

    for value in trusted_terms[:6]:
        output.append(("term", value))
    for value in trusted_related_terms[:8]:
        output.append(("related", value))
    for value in trusted_questions[:8]:
        output.append(("question", value))
    for value in supporting_related_terms[:6]:
        output.append(("related", value))
    for value in cluster.get("lineage_roots", []):
        output.append(("root", value))
    return output


def _extract_workflow_or_pain(text: str, fallback: str) -> str:
    tokens = [token for token in founder_core_tokens(text) if token not in WORKFLOW_STOPWORDS]
    if not tokens:
        tokens = [token for token in founder_core_tokens(fallback) if token not in WORKFLOW_STOPWORDS]
    if not tokens:
        return ""
    return " ".join(tokens[:4])


def _extract_target_context(text: str, cluster_title: str) -> str:
    lowered = text.lower()
    for pattern, label in CONTEXT_PATTERNS:
        if pattern.search(lowered):
            return label

    for_match = re.search(r"\bfor ([a-z0-9][a-z0-9 -]{2,40})", lowered)
    if for_match:
        fragment = re.sub(r"\b(" + "|".join(INTENT_MARKERS) + r")\b", "", for_match.group(1))
        cleaned = " ".join(token for token in content_tokens(fragment) if token not in CONTEXT_STOPWORDS)
        if cleaned:
            return cleaned

    if "small business" in cluster_title.lower():
        return CONTEXT_FALLBACK
    return "operators"


def _derive_offer(text: str) -> str:
    for marker in INTENT_MARKERS:
        if marker in text:
            return OFFER_MAP.get(marker, "workflow pack")
    return "workflow pack"


def _build_label(workflow: str, context: str) -> str:
    label = workflow
    if context and context not in workflow:
        label = f"{workflow} for {context}"
    return label.strip()


def _build_advice(label: str, offer: str, supporting_terms: list[str], rejection_reason: str | None) -> str:
    if rejection_reason:
        if rejection_reason == "weak evidence":
            return f"Evidence is too thin to recommend `{label}` yet. Keep collecting examples before making a founder-style call."
        if rejection_reason == "too broad":
            return f"`{label}` still reads too broad. Push toward one narrower workflow or pain before treating it as a real bet."
        return f"`{label}` has signal, but not enough specificity to advise on honestly yet."

    anchors = ", ".join(supporting_terms[:2]) if supporting_terms else label
    return f"Start with a {offer} around `{label}` and validate it against signals like {anchors}."


def _placeholder_candidate(cluster: dict) -> dict:
    return {
        "label": cluster["title_seed"],
        "workflow_or_pain": cluster["title_seed"],
        "supporting_terms": cluster.get("terms", [])[:2],
        "supporting_questions": cluster.get("questions", [])[:2],
        "evidence_refs": [],
        "specificity_score": 0.0,
        "advice": f"`{cluster['title_seed']}` is not specific enough to advise on honestly.",
        "rejection_reason": "too broad",
        "source_kinds": [],
    }
