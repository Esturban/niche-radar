from __future__ import annotations

from collections import defaultdict

from .utils import DISCOVERY_SIGNAL_TOKENS, content_tokens

SIGNAL_FAMILIES = {
    "analytics": "small business analytics",
    "automation": "small business automation",
    "dashboard": "small business dashboard",
    "integration": "small business automation",
    "integrations": "small business automation",
    "operations": "small business operations",
    "optimization": "small business operations",
    "report": "small business reporting",
    "reporting": "small business reporting",
    "research": "small business research workflows",
    "seo": "small business seo workflows",
    "strategy": "small business strategy workflows",
    "visualization": "small business dashboards",
    "workflow": "small business workflow automation",
    "workflows": "small business workflow automation",
}


def cluster_terms(term_states: dict[str, dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for term, state in term_states.items():
        grouped[_cluster_key(term)].append(state)

    clusters: list[dict] = []
    for cluster_id, items in grouped.items():
        all_hits = [hit for item in items for hit in item["hits"]]
        question_hits = [hit for hit in all_hits if hit.get("question_like")]
        related_terms = sorted({hit.get("text") for hit in all_hits if hit.get("text")})
        generations = sorted({item["generation"] for item in items})
        lineage_roots = sorted({item["lineage_root"] for item in items})
        clusters.append(
            {
                "cluster_id": cluster_id,
                "title_seed": _select_title_seed(items, cluster_id),
                "terms": sorted(item["term"] for item in items),
                "items": items,
                "generations": generations,
                "lineage_roots": lineage_roots,
                "questions": sorted({hit.get("text") for hit in question_hits if hit.get("text")}),
                "related_terms": related_terms,
            }
        )

    return clusters


def build_question_graph(clusters: list[dict]) -> dict:
    nodes = []
    edges = []
    seen_nodes: set[str] = set()
    for cluster in clusters:
        cluster_node = cluster["title_seed"]
        if cluster_node not in seen_nodes:
            nodes.append({"id": cluster_node, "type": "cluster"})
            seen_nodes.add(cluster_node)
        for question in cluster["questions"]:
            if question not in seen_nodes:
                nodes.append({"id": question, "type": "question"})
                seen_nodes.add(question)
            edges.append({"from": cluster_node, "to": question, "kind": "question"})
    return {"nodes": nodes, "edges": edges}


def _cluster_key(term: str) -> str:
    tokens = content_tokens(term)
    for token in tokens:
        if token in SIGNAL_FAMILIES:
            return SIGNAL_FAMILIES[token]

    matching = [token for token in tokens if token in DISCOVERY_SIGNAL_TOKENS]
    if matching:
        return f"small business {matching[0]}"
    return term


def _select_title_seed(items: list[dict], cluster_id: str) -> str:
    if cluster_id.startswith("small business"):
        return cluster_id
    preferred = sorted(
        items,
        key=lambda item: (
            -item.get("trend_strength_raw", 0.0),
            -item.get("adjacency_count_raw", 0.0),
            item["generation"],
            len(item["term"]),
        ),
    )
    for item in preferred:
        tokens = content_tokens(item["term"])
        if len(tokens) <= 3:
            return item["term"]
    return cluster_id if cluster_id.startswith("small business") else preferred[0]["term"]
