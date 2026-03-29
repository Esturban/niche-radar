from __future__ import annotations

from .evolve import lineage_generations
from .utils import clamp01, content_tokens, minmax_scale, safe_mean


def score_clusters(clusters: list[dict], profile: dict, total_generations: int) -> tuple[list[dict], list[dict]]:
    profile_vocab = set(profile.get("keywords", []) + profile.get("phrases", []) + profile.get("themes", []))
    lineage_map = lineage_generations(
        [
            # reconstructed light-weight records
            type("Record", (), {"lineage_root": item["lineage_root"], "generation": item["generation"]})
            for cluster in clusters
            for item in cluster["items"]
        ]
    )

    raw_fit: dict[str, float] = {}
    raw_strength: dict[str, float] = {}
    raw_velocity: dict[str, float] = {}
    raw_adjacency: dict[str, float] = {}
    raw_question: dict[str, float] = {}
    raw_surface: dict[str, float] = {}
    raw_survival: dict[str, float] = {}

    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        tokens = set(token for term in cluster["terms"] for token in content_tokens(term))
        raw_fit[cluster_id] = len(tokens & profile_vocab) / max(1, len(tokens))
        raw_strength[cluster_id] = max(item.get("trend_strength_raw", 0.0) for item in cluster["items"])
        raw_velocity[cluster_id] = max(item.get("trend_velocity_raw", 0.0) for item in cluster["items"])
        raw_adjacency[cluster_id] = float(len(cluster["related_terms"]))
        raw_question[cluster_id] = float(len(cluster["questions"]))
        raw_surface[cluster_id] = safe_mean(item.get("surface_spread_raw", 0.0) for item in cluster["items"])
        survivals = [len(lineage_map.get(root, set())) / max(1, total_generations) for root in cluster["lineage_roots"]]
        raw_survival[cluster_id] = safe_mean(survivals)

    fit = minmax_scale(raw_fit)
    strength = minmax_scale(raw_strength)
    velocity = minmax_scale(raw_velocity)
    adjacency = minmax_scale(raw_adjacency)
    question = minmax_scale(raw_question)
    surface = minmax_scale(raw_surface)
    survival = minmax_scale(raw_survival)

    scored: list[dict] = []
    for cluster in clusters:
        cluster_id = cluster["cluster_id"]
        confidence = clamp01(
            (
                fit.get(cluster_id, 0.0)
                + strength.get(cluster_id, 0.0)
                + adjacency.get(cluster_id, 0.0)
                + surface.get(cluster_id, 0.0)
                + survival.get(cluster_id, 0.0)
            )
            / 5
        )
        total_score = clamp01(
            fit.get(cluster_id, 0.0) * 0.24
            + strength.get(cluster_id, 0.0) * 0.18
            + velocity.get(cluster_id, 0.0) * 0.14
            + survival.get(cluster_id, 0.0) * 0.14
            + adjacency.get(cluster_id, 0.0) * 0.12
            + question.get(cluster_id, 0.0) * 0.10
            + surface.get(cluster_id, 0.0) * 0.08
        )
        scored.append(
            {
                **cluster,
                "title": cluster["title_seed"],
                "profile_fit_score": round(fit.get(cluster_id, 0.0), 4),
                "trend_strength": round(strength.get(cluster_id, 0.0), 4),
                "trend_velocity": round(velocity.get(cluster_id, 0.0), 4),
                "batch_survival_score": round(survival.get(cluster_id, 0.0), 4),
                "adjacency_score": round(adjacency.get(cluster_id, 0.0), 4),
                "question_density": round(question.get(cluster_id, 0.0), 4),
                "surface_spread": round(surface.get(cluster_id, 0.0), 4),
                "confidence": round(confidence, 4),
                "total_score": round(total_score, 4),
                "validation_needed": True,
                "competition_surface_proxy": None,
            }
        )

    ranked = sorted(scored, key=lambda cluster: (cluster["total_score"], cluster["confidence"]), reverse=True)
    return ranked, scored

