#!/usr/bin/env python3
"""Definitive PIT runner with fail-closed ranked-active CMC slug recovery.

Research-only identity layer on top of the DYDX-segmented definitive runner.
Only still-unresolved historical rows may be resolved, only by the exact CMC
historical currency slug, and only when the rank-sorted active CMC map has one
unique standard-ASCII ticker for that slug. Existing identities are never
overwritten and any historical/current slug conflict remains unresolved.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import gate_btc_cmc_ranked_active_identity as ranked
import gate_btc_survivorship_definitive_dydx_segmented_runner as dydx

COLLECTOR = dydx.continuity.staged.runner.cmc_collector


def _historical_slug_symbols(snapshots: pd.DataFrame) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    resolved = snapshots[snapshots["identity_resolved"].astype(bool)]
    for row in resolved.itertuples(index=False):
        slug = ranked.norm(getattr(row, "cmc_slug", ""))
        symbol = str(getattr(row, "symbol", "")).upper().strip()
        if slug and symbol:
            out.setdefault(slug, set()).add(symbol)
    return out


def _resolve_unresolved_ranked_slugs(snapshots: pd.DataFrame, ranked_rows: list[dict]) -> tuple[pd.DataFrame, dict]:
    out = snapshots.copy()
    pre_unresolved = int((~out["identity_resolved"].astype(bool)).sum())
    slug_map, _ = ranked.ranked_identity_maps(ranked_rows)
    historical = _historical_slug_symbols(out)

    unique_ranked = {slug: next(iter(symbols)) for slug, symbols in slug_map.items() if len(symbols) == 1}
    ranked_ambiguous = {slug: sorted(symbols) for slug, symbols in slug_map.items() if len(symbols) > 1}
    historical_conflicts = {}
    for slug, symbol in list(unique_ranked.items()):
        prior = historical.get(slug, set())
        if prior and prior != {symbol}:
            historical_conflicts[slug] = {"historical": sorted(prior), "ranked_active": symbol}
            unique_ranked.pop(slug, None)

    resolved_rows = 0
    resolved_slugs: dict[str, str] = {}
    for idx, row in out[~out["identity_resolved"].astype(bool)].iterrows():
        slug = ranked.norm(row.get("cmc_slug", ""))
        symbol = unique_ranked.get(slug)
        if not slug or not symbol:
            continue
        out.at[idx, "symbol"] = symbol
        out.at[idx, "symbol_resolution"] = "CMC_RANKED_ACTIVE_SLUG_MAP"
        out.at[idx, "identity_resolved"] = True
        resolved_rows += 1
        resolved_slugs[slug] = symbol

    post_unresolved = int((~out["identity_resolved"].astype(bool)).sum())
    policy = {
        "schema": "gate_btc.cmc_ranked_active_slug_identity.v1",
        "status": "PASS_EXACT_UNRESOLVED_SLUG_ONLY",
        "ranked_rows": len(ranked_rows),
        "pre_unresolved_rows": pre_unresolved,
        "post_unresolved_rows": post_unresolved,
        "resolved_rows": resolved_rows,
        "resolved_unique_slugs": len(resolved_slugs),
        "resolved_slug_symbols": dict(sorted(resolved_slugs.items())),
        "ranked_ambiguous_slug_count": len(ranked_ambiguous),
        "ranked_ambiguous_slugs": ranked_ambiguous,
        "historical_conflict_count": len(historical_conflicts),
        "historical_conflicts": historical_conflicts,
        "existing_identity_overwrite_allowed": False,
        "name_based_ranked_backfill_allowed": False,
        "exact_historical_slug_required": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    return out, policy


def _collect_snapshots_ranked(session, outdir: Path) -> pd.DataFrame:
    snapshots = dydx._collect_snapshots_segmented(session, outdir)
    ranked_rows = ranked.fetch_ranked_active_rows(session)
    sentinels = ranked.sentinel_report(ranked_rows)
    if not sentinels["core_pass"]:
        raise RuntimeError("CMC ranked-active core identity sentinels failed")
    resolved, policy = _resolve_unresolved_ranked_slugs(snapshots, ranked_rows)
    policy["sentinels"] = sentinels
    resolved.to_csv(outdir / "CMC_MONTH_END_TOP150.csv", index=False)
    unresolved = resolved[~resolved["identity_resolved"].astype(bool)][
        ["snapshot_date", "rank", "name", "symbol", "cmc_slug"]
    ]
    unresolved.to_csv(outdir / "CMC_UNRESOLVED_IDENTITIES.csv", index=False)
    (outdir / "CMC_RANKED_ACTIVE_SLUG_IDENTITY_POLICY.json").write_text(
        json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        "CMC_RANKED_ACTIVE_SLUG_RECOVERY=PASS "
        f"resolved_rows={policy['resolved_rows']} unresolved={policy['post_unresolved_rows']} "
        f"unique_slugs={policy['resolved_unique_slugs']} conflicts={policy['historical_conflict_count']}",
        flush=True,
    )
    return resolved


def apply_ranked_active_slug_identity() -> None:
    dydx.apply_dydx_segmentation()
    COLLECTOR.collect_snapshots = _collect_snapshots_ranked


def main() -> int:
    apply_ranked_active_slug_identity()
    return dydx.continuity.main()


if __name__ == "__main__":
    raise SystemExit(main())
