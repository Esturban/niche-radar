from __future__ import annotations

from collections import defaultdict

from .utils import content_tokens, shared_token_score


def cluster_terms(term_states: dict[str, dict]) -> list[dict]:
    terms = list(term_states)
    parents: dict[str, str] = {term: term for term in terms}

    def find(term: str) -> str:
        while parents[term] != term:
            parents[term] = parents[parents[term]]
            term = parents[term]
        return term

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parents[root_right] = root_left

    for index, left in enumerate(terms):
        for right in terms[index + 1 :]:
            overlap = shared_token_score(left, right)
            left_tokens = set(content_tokens(left))
            right_tokens = set(content_tokens(right))
            if overlap >= 0.34 or len(left_tokens & right_tokens) >= 2:
                union(left, right)

    grouped: dict[str, list[dict]] = defaultdict(list)
    for term, state in term_states.items():
        grouped[find(term)].append(state)

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
                "title_seed": max(items, key=lambda item: (item.get("trend_strength_raw", 0.0), item.get("adjacency_count_raw", 0.0), item["generation"]))["term"],
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

