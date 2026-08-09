#!/usr/bin/env python3
"""Definitive PIT wrapper with fail-closed dYdX token-era segmentation.

Research-only identity correction layered on the existing continuity runner.
Historical CMC rows with slug ``dydx`` strictly before dYdX Chain genesis are
assigned the explicit audit identity ``DYDXERC20``. Native-chain ``DYDX`` is
kept separate and blocked from generic history recovery. The bounded legacy
segment uses exactly one direct exchange source and is never stitched to native
DYDX or post-genesis ethDYDX.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import gate_btc_survivorship_definitive_cc_first_continuity_runner as continuity

CHAIN_GENESIS = pd.Timestamp("2023-10-26")
LEGACY_SYMBOL = "DYDXERC20"
LEGACY_CMC_SLUG = "dydx"
NATIVE_SYMBOL = "DYDX"
NATIVE_CMC_SLUG = "dydxchain"
POST_GENESIS_ETH_SYMBOL = "ETHDYDX"
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]

_ORIGINAL_CMC_COLLECT = continuity.staged.runner.cmc_collector.collect_snapshots
_ORIGINAL_IDENTITY_AUDIT = continuity._identity_audit_with_single_char_evidence
_ORIGINAL_HISTORY_COLLECT = continuity._collect_histories_with_residual_recovery


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _segment_snapshots(snapshots: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = snapshots.copy()
    dates = pd.to_datetime(out["snapshot_date"], errors="raise").dt.tz_localize(None)
    slugs = out.get("cmc_slug", pd.Series("", index=out.index)).astype(str).map(continuity._norm)
    symbols = out["symbol"].astype(str)
    mask = symbols.eq(NATIVE_SYMBOL) & slugs.eq(LEGACY_CMC_SLUG) & dates.lt(CHAIN_GENESIS)

    touched = out.loc[mask, [c for c in ["snapshot_date", "rank", "name", "symbol", "cmc_slug"] if c in out.columns]].copy()
    if not touched.empty:
        out.loc[mask, "symbol"] = LEGACY_SYMBOL
        if "symbol_resolution" in out.columns:
            out.loc[mask, "symbol_resolution"] = "CURATED_DYDX_PRE_GENESIS_SEGMENT"
        if "identity_resolved" in out.columns:
            out.loc[mask, "identity_resolved"] = True

    # Fail closed if the transform ever touches a native-chain slug or a date on
    # or after chain genesis.
    changed = out["symbol"].astype(str).eq(LEGACY_SYMBOL)
    changed_dates = pd.to_datetime(out.loc[changed, "snapshot_date"], errors="raise").dt.tz_localize(None)
    changed_slugs = out.loc[changed].get("cmc_slug", pd.Series("", index=out.loc[changed].index)).astype(str).map(continuity._norm)
    if bool((changed_dates >= CHAIN_GENESIS).any()):
        raise RuntimeError("DYDXERC20 segment crosses dYdX Chain genesis")
    if bool((changed_slugs != LEGACY_CMC_SLUG).any()):
        raise RuntimeError("DYDXERC20 segment contains a non-legacy CMC slug")
    return out, touched


def _write_identity_policy(outdir: Path, touched: pd.DataFrame) -> None:
    dates = pd.to_datetime(touched["snapshot_date"], errors="coerce") if not touched.empty else pd.Series(dtype="datetime64[ns]")
    payload = {
        "schema": "gate_btc.dydx_segmented_identity.v1",
        "status": "RESEARCH_ONLY_FAIL_CLOSED_SEGMENTATION",
        "chain_genesis": str(CHAIN_GENESIS.date()),
        "legacy_cmc_slug": LEGACY_CMC_SLUG,
        "legacy_audit_symbol": LEGACY_SYMBOL,
        "legacy_snapshot_rows": int(len(touched)),
        "legacy_first_snapshot": str(dates.min().date()) if len(dates) else None,
        "legacy_last_snapshot": str(dates.max().date()) if len(dates) else None,
        "native_symbol": NATIVE_SYMBOL,
        "native_cmc_slug": NATIVE_CMC_SLUG,
        "post_genesis_ethereum_symbol": POST_GENESIS_ETH_SYMBOL,
        "native_dydx_generic_history_allowed": False,
        "post_genesis_ethdydx_stitched_to_native": False,
        "cross_token_stitching": False,
        "synthetic_conversion": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    (outdir / "DYDX_SEGMENT_IDENTITY_POLICY.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _collect_snapshots_segmented(session, outdir: Path) -> pd.DataFrame:
    snapshots = _ORIGINAL_CMC_COLLECT(session, outdir)
    segmented, touched = _segment_snapshots(snapshots)
    if touched.empty:
        raise RuntimeError("expected historical dYdX pre-genesis snapshots were not found")
    segmented.to_csv(outdir / "CMC_MONTH_END_TOP150.csv", index=False)
    _write_identity_policy(outdir, touched)
    dates = pd.to_datetime(touched["snapshot_date"])
    print(
        "DYDX_PIT_SEGMENT=PASS "
        f"rows={len(touched)} first={dates.min().date()} last={dates.max().date()} "
        f"genesis={CHAIN_GENESIS.date()}",
        flush=True,
    )
    return segmented


def _identity_audit_segmented(snapshots, coinlist, v2a):
    identity = _ORIGINAL_IDENTITY_AUDIT(snapshots, coinlist, v2a)

    legacy_mask = identity["symbol"].astype(str).eq(LEGACY_SYMBOL)
    if not bool(legacy_mask.any()):
        raise RuntimeError("DYDXERC20 identity row missing after snapshot segmentation")
    identity.loc[legacy_mask, "history_usable"] = False
    identity.loc[legacy_mask, "exchange_identity_ok"] = False
    identity.loc[legacy_mask, "identity_confidence"] = "CURATED_DYDX_PRE_GENESIS_AWAITING_BOUNDED_SOURCE"
    identity.loc[legacy_mask, "history_source"] = ""
    identity.loc[legacy_mask, "history_rows"] = 0

    # Native DYDX must not inherit the exchange ticker's pre-genesis history.
    native_mask = identity["symbol"].astype(str).eq(NATIVE_SYMBOL)
    if bool(native_mask.any()):
        identity.loc[native_mask, "history_usable"] = False
        identity.loc[native_mask, "exchange_identity_ok"] = False
        identity.loc[native_mask, "identity_confidence"] = "BLOCKED_NATIVE_DYDX_NO_UNBOUNDED_TICKER_HISTORY"
        identity.loc[native_mask, "history_source"] = ""
        identity.loc[native_mask, "history_rows"] = 0
    return identity


def _bounded_exchange_history(raw: pd.DataFrame, venue: str) -> pd.DataFrame:
    return continuity._bounded_relabel(
        raw,
        LEGACY_SYMBOL,
        f"{venue}_dydx_usdt_pre_genesis_erc20",
        end_exclusive=CHAIN_GENESIS,
    )


def _strictly_spans_segment(history: pd.DataFrame, first_snapshot, last_snapshot) -> bool:
    if history is None or history.empty:
        return False
    first = pd.Timestamp(first_snapshot).tz_localize(None).normalize()
    last = pd.Timestamp(last_snapshot).tz_localize(None).normalize()
    dates = pd.to_datetime(history["date"], errors="coerce").dropna().dt.tz_localize(None).dt.normalize()
    if dates.empty or bool((dates >= CHAIN_GENESIS).any()):
        return False
    member = dates[(dates >= first) & (dates <= last + pd.Timedelta(days=35))]
    if member.empty:
        return False
    return bool(member.min() <= first + pd.Timedelta(days=7) and member.max() >= last)


def _recover_legacy_segment(session, identity_row) -> tuple[pd.DataFrame, str, dict]:
    candidates: list[pd.DataFrame] = []
    evidence = []
    for venue, fetcher in (
        ("gateio", continuity.staged.runner.exchange_history.fetch_gate),
        ("kucoin", continuity.staged.runner.exchange_history.fetch_kucoin),
    ):
        try:
            raw, raw_status = fetcher(session, "DYDX")
        except Exception as exc:
            raw, raw_status = _empty(), f"ERROR_{type(exc).__name__}"
        bounded = _bounded_exchange_history(raw, venue)
        spans = _strictly_spans_segment(bounded, identity_row.first_snapshot, identity_row.last_snapshot)
        evidence.append({
            "venue": venue,
            "raw_status": raw_status,
            "rows": int(len(bounded)),
            "first_date": str(bounded["date"].min().date()) if not bounded.empty else None,
            "last_date": str(bounded["date"].max().date()) if not bounded.empty else None,
            "strict_span": spans,
        })
        if spans:
            candidates.append(bounded)
    if not candidates:
        return _empty(), "", {"status": "NO_SINGLE_SOURCE_STRICT_SPAN", "evidence": evidence}

    best, source = continuity.staged.runner._choose_source(
        candidates,
        pd.Timestamp(identity_row.first_snapshot),
        pd.Timestamp(identity_row.last_snapshot),
    )
    if best.empty or not _strictly_spans_segment(best, identity_row.first_snapshot, identity_row.last_snapshot):
        return _empty(), "", {"status": "NO_SINGLE_SOURCE_STRICT_SPAN", "evidence": evidence}
    return best[COLS].copy(), source, {"status": "PASS_SINGLE_SOURCE_BOUNDED", "evidence": evidence}


def _collect_histories_segmented(session, identity: pd.DataFrame, outdir: Path):
    master, cov = _ORIGINAL_HISTORY_COLLECT(session, identity, outdir)
    legacy_rows = identity[identity["symbol"].astype(str).eq(LEGACY_SYMBOL)]
    if len(legacy_rows) != 1:
        raise RuntimeError(f"expected one DYDXERC20 identity row, got {len(legacy_rows)}")
    ir = legacy_rows.iloc[0]
    history, source, result = _recover_legacy_segment(session, ir)

    recovery_payload = {
        "schema": "gate_btc.dydx_segmented_recovery.v1",
        "status": result["status"],
        "legacy_symbol": LEGACY_SYMBOL,
        "chain_genesis_exclusive": str(CHAIN_GENESIS.date()),
        "selected_source": source,
        "rows": int(len(history)),
        "first_date": str(history["date"].min().date()) if not history.empty else None,
        "last_date": str(history["date"].max().date()) if not history.empty else None,
        "venue_evidence": result["evidence"],
        "one_continuous_source_per_symbol": True,
        "cross_token_stitching": False,
        "native_dydx_recovery_attempted": False,
        "source_substitution_into_frozen_engine": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    (outdir / "DYDX_SEGMENT_RECOVERY.json").write_text(
        json.dumps(recovery_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    pd.DataFrame(result["evidence"]).to_csv(outdir / "DYDX_SEGMENT_RECOVERY_EVIDENCE.csv", index=False)

    if history.empty:
        print("DYDX_SEGMENT_RECOVERY=FAIL_CLOSED", flush=True)
        return master, cov

    combined = master[~master["symbol"].astype(str).eq(LEGACY_SYMBOL)].copy()
    combined = pd.concat([combined, history], ignore_index=True)
    combined = combined.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")

    cov = cov.copy()
    mask = cov["symbol"].astype(str).eq(LEGACY_SYMBOL)
    if not bool(mask.any()):
        raise RuntimeError("DYDXERC20 coverage row missing")
    cov.loc[mask, "status"] = "PASS"
    cov.loc[mask, "rows"] = len(history)
    cov.loc[mask, "first_date"] = history["date"].min()
    cov.loc[mask, "last_date"] = history["date"].max()
    cov.loc[mask, "selected_source"] = source
    if "residual_recovery_rows" in cov.columns:
        cov.loc[mask, "residual_recovery_rows"] = len(history)

    imask = identity["symbol"].astype(str).eq(LEGACY_SYMBOL)
    identity.loc[imask, "history_usable"] = True
    identity.loc[imask, "history_source"] = source
    identity.loc[imask, "history_rows"] = len(history)
    identity.loc[imask, "identity_confidence"] = "CURATED_DYDX_PRE_GENESIS_SEGMENT_PASS"

    # Re-assert that native DYDX remains blocked after all underlying recovery layers.
    native = identity["symbol"].astype(str).eq(NATIVE_SYMBOL)
    if bool(native.any()):
        identity.loc[native, "history_usable"] = False
        identity.loc[native, "history_source"] = ""
        identity.loc[native, "history_rows"] = 0
        identity.loc[native, "exchange_identity_ok"] = False
        identity.loc[native, "identity_confidence"] = "BLOCKED_NATIVE_DYDX_NO_UNBOUNDED_TICKER_HISTORY"
        nmask = cov["symbol"].astype(str).eq(NATIVE_SYMBOL)
        if bool(nmask.any()):
            cov.loc[nmask, "status"] = "NO_USABLE_HISTORY"
            cov.loc[nmask, "rows"] = 0
            cov.loc[nmask, "first_date"] = None
            cov.loc[nmask, "last_date"] = None
            cov.loc[nmask, "selected_source"] = ""

    combined.to_csv(outdir / "CASCADE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CASCADE_COVERAGE.csv", index=False)
    identity.to_csv(outdir / "IDENTITY_AUDIT.csv", index=False)

    summary_path = outdir / "SOURCE_CASCADE_SUMMARY.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    summary["history_pass"] = int((cov["status"] == "PASS").sum())
    counts = cov.loc[
        (cov["status"] == "PASS") & cov["selected_source"].fillna("").ne(""),
        "selected_source",
    ].astype(str).value_counts().to_dict()
    summary["selected_sources"] = {str(k): int(v) for k, v in sorted(counts.items())}
    summary["dydx_segmented_recovery"] = {
        "status": result["status"],
        "legacy_symbol": LEGACY_SYMBOL,
        "selected_source": source,
        "rows": int(len(history)),
        "native_dydx_blocked": True,
        "cross_token_stitching": False,
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"DYDX_SEGMENT_RECOVERY=PASS symbol={LEGACY_SYMBOL} rows={len(history)} source={source}",
        flush=True,
    )
    return combined, cov


def apply_dydx_segmentation() -> None:
    continuity.staged.runner.cmc_collector.collect_snapshots = _collect_snapshots_segmented
    continuity._identity_audit_with_single_char_evidence = _identity_audit_segmented
    continuity._collect_histories_with_residual_recovery = _collect_histories_segmented


def main() -> int:
    apply_dydx_segmentation()
    return continuity.main()


if __name__ == "__main__":
    raise SystemExit(main())
