from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase306_315_stability_common import (
    ROOT,
    base_payload,
    fingerprint,
    pearson,
    read_json,
    validate_phase,
    write_json,
    write_phase_summary,
)


def _clusters(ids: list[str], correlations: dict[str, dict[str, float]], threshold: float) -> list[list[str]]:
    parent = {item: item for item in ids}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for index, left in enumerate(ids):
        for right in ids[index + 1 :]:
            if abs(correlations[left][right]) >= threshold:
                union(left, right)

    grouped: dict[str, list[str]] = defaultdict(list)
    for item in ids:
        grouped[find(item)].append(item)
    return sorted((sorted(group) for group in grouped.values()), key=lambda group: (-len(group), group))


def build(phase303_path: Path, phase304_path: Path, output_dir: Path) -> dict[str, Any]:
    phase303 = read_json(phase303_path)
    phase304 = read_json(phase304_path)
    validate_phase(phase303, 303)
    validate_phase(phase304, 304)

    hypotheses = phase303.get("hypotheses", [])
    ids = [str(item["hypothesis_id"]) for item in hypotheses]
    if len(ids) != int(phase303.get("experiment_budget", 0)):
        raise RuntimeError("Hypothesis registry and hard budget differ.")

    vectors: dict[str, list[float]] = {item: [] for item in ids}
    for fold in phase304.get("fold_results", []):
        results = fold.get("inner_selection", {}).get("results", {})
        for item in ids:
            if item not in results:
                raise RuntimeError(f"Fold is missing registered hypothesis {item}.")
            vectors[item].append(float(results[item].get("mean_per_10000_brl", 0.0)))
    if not vectors or min(len(values) for values in vectors.values()) < 3:
        raise RuntimeError("Insufficient fold vectors for hypothesis dependence audit.")

    correlations: dict[str, dict[str, float]] = {item: {} for item in ids}
    high_pairs: list[dict[str, Any]] = []
    for index, left in enumerate(ids):
        for right in ids:
            correlations[left][right] = pearson(vectors[left], vectors[right])
        for right in ids[index + 1 :]:
            value = correlations[left][right]
            if abs(value) >= 0.90:
                high_pairs.append({"left": left, "right": right, "correlation": value})

    clusters = _clusters(ids, correlations, 0.90)
    effective_count = len(clusters)
    effective_ratio = effective_count / len(ids) if ids else 0.0
    largest_cluster = len(clusters[0]) if clusters else 0
    largest_cluster_share = largest_cluster / len(ids) if ids else 0.0
    duplicate_vector_pairs = sum(
        vectors[left] == vectors[right]
        for index, left in enumerate(ids)
        for right in ids[index + 1 :]
    )
    family_counts = Counter(str(item["family"]) for item in hypotheses)
    max_family_share = max(family_counts.values()) / len(ids) if ids else 0.0

    dependency_pass = (
        effective_ratio >= 0.50
        and largest_cluster_share <= 0.35
        and duplicate_vector_pairs == 0
        and max_family_share <= 0.50
    )
    reasons: list[str] = []
    if effective_ratio < 0.50:
        reasons.append("EFFECTIVE_INDEPENDENT_HYPOTHESIS_RATIO_BELOW_50_PERCENT")
    if largest_cluster_share > 0.35:
        reasons.append("LARGEST_DEPENDENCY_CLUSTER_TOO_LARGE")
    if duplicate_vector_pairs:
        reasons.append("DUPLICATE_PERFORMANCE_VECTORS")
    if max_family_share > 0.50:
        reasons.append("REGISTRY_DOMINATED_BY_ONE_FAMILY")

    payload = base_payload(308, "HYPOTHESIS_DEPENDENCE_AUDITED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE308_HYPOTHESIS_DEPENDENCE_AUDIT_READY_RESEARCH_ONLY",
            "phase303_artifact": phase303_path.relative_to(ROOT).as_posix(),
            "phase303_fingerprint": phase303.get("artifact_fingerprint"),
            "phase304_artifact": phase304_path.relative_to(ROOT).as_posix(),
            "phase304_fingerprint": phase304.get("artifact_fingerprint"),
            "registered_hypothesis_count": len(ids),
            "fold_vector_length": min(len(values) for values in vectors.values()),
            "correlation_threshold": 0.90,
            "high_correlation_pair_count": len(high_pairs),
            "high_correlation_pairs": high_pairs,
            "dependency_clusters": clusters,
            "effective_independent_hypothesis_count": effective_count,
            "effective_independent_ratio": effective_ratio,
            "largest_cluster_size": largest_cluster,
            "largest_cluster_share": largest_cluster_share,
            "duplicate_vector_pair_count": duplicate_vector_pairs,
            "family_counts": dict(sorted(family_counts.items())),
            "max_family_share": max_family_share,
            "dependency_pass": dependency_pass,
            "failure_reasons": reasons,
            "experiment_budget_unchanged": True,
            "new_hypotheses_added": 0,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase308_hypothesis_dependence_audit.json", payload)
    write_phase_summary(
        ROOT / "docs/reports/stability_v2/phase308_hypothesis_dependence_audit_summary.md",
        title="Phase 308 — Hypothesis Dependence Audit",
        gate=payload["gate"],
        bullets=[
            f"Registered hypotheses: `{len(ids)}`",
            f"Hard budget unchanged: `True`",
            f"New hypotheses added: `0`",
            f"High-correlation pairs: `{len(high_pairs)}`",
            f"Effective independent hypotheses: `{effective_count}/{len(ids)}`",
            f"Largest dependency-cluster share: `{largest_cluster_share:.2%}`",
            f"Dependency pass: `{dependency_pass}`",
            f"Failure reasons: `{', '.join(reasons) if reasons else 'NONE'}`",
            "Strategy approved: `False`",
        ],
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase303-artifact",
        type=Path,
        default=ROOT / "artifacts/phase303_finite_hypothesis_registry_v2_research_only/phase303_finite_hypothesis_registry_v2.json",
    )
    parser.add_argument(
        "--phase304-artifact",
        type=Path,
        default=ROOT / "artifacts/phase304_nested_walk_forward_v2_research_only/phase304_nested_walk_forward_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase308_hypothesis_dependence_audit_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase303_artifact, args.phase304_artifact, args.output_dir)
    print(payload["gate"])
    print("Registered hypotheses:", payload["registered_hypothesis_count"])
    print("Effective independent hypotheses:", payload["effective_independent_hypothesis_count"])
    print("Dependency pass:", payload["dependency_pass"])
    print("Experiment budget unchanged:", payload["experiment_budget_unchanged"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
