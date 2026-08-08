#!/usr/bin/env python3
"""Run staged direct-USD PIT recovery with evidence-backed continuities.

Research-only wrapper layered on the CC-first staging runner. It keeps the
trade-level Bybit archive deferred and adds only primary-source documented
identity continuities, classification corrections, and tightly bounded
historical-label recovery. No strategy, factor, weight, price, return,
execution, or frozen-engine rule is changed.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd

import gate_btc_survivorship_definitive_cc_first_runner as staged

EVIDENCE_BACKED_CONTINUITIES = {
    "THETA": {"theta", "thetanetwork"},
    "HBAR": {"hedera", "hederahashgraph"},
    "FET": {"fetchai", "artificialsuperintelligencealliance"},
    "INJ": {"injective", "injectiveprotocol"},
    "SNX": {"synthetix", "synthetixnetworktoken"},
    "SXP": {"sxp", "solar", "swipe"},
}

# PIT-only single-character ticker exceptions backed by primary project evidence.
# This does not modify the canonical V2A standard_ticker rule and does not admit
# any other one-character symbol.
EVIDENCE_BACKED_SINGLE_CHAR = {
    "W": {"name": "wormhole", "slug": "wormhole"},
    "T": {"name": "threshold", "slug": "threshold"},
}

# Stablecoin identities missing from the frozen symbol/name filter because CMC
# now exposes historical markets under later/current labels. These exact
# symbol+name pairs are excluded from the directional PIT universe; the
# canonical V2A stable list is not modified.
EVIDENCE_BACKED_PIT_STABLES = {
    "XTN": {"neutrinousd"},
    "FEI": {"feiusd"},
}

# Explicit historical-label recovery boundaries. These do NOT establish
# same-token continuity across the boundary. They permit only the documented
# historical market label/API identifier during the snapshot window that
# predates (or postdates, for REV) the migration event.
BORG_MIGRATION_DATE = pd.Timestamp("2023-10-17")
BTT_REDENOMINATION_DATE = pd.Timestamp("2021-12-27")
REV_RENAME_COMPLETE_DATE = pd.Timestamp("2020-04-09")
MEXC_HISTORY_START = pd.Timestamp("2023-01-01")
MEXC_END = pd.Timestamp("2026-08-06")
RESIDUAL_SYMBOLS = ("BORG", "BTTOLD", "REV", "MX")
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]

# Intentionally absent from same-token continuity:
# - DYDX / ethDYDX: documented bridge/conversion across chains/tokens.
# - KNC / KNCL: documented old-contract to new-contract token migration.
# - BORG / CHSB and BTTOLD / BTT: token migrations/redenominations are not
#   admitted by the continuity layer. Their legacy identifiers may only be used
#   inside the hard-bounded historical recovery functions below.

_ORIGINAL_IDENTITY_AUDIT = staged.runner._cascade_identity_audit
_ORIGINAL_STABLE_SYMBOL = staged.runner.definitive.stable_symbol
_ORIGINAL_COLLECT_HISTORIES = staged.runner._cascade_collect_histories


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _norm(value: object) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _single_char_evidence_ok(symbol: str, names: list[str], slugs: list[str]) -> bool:
    evidence = EVIDENCE_BACKED_SINGLE_CHAR.get(str(symbol))
    if evidence is None:
        return False
    name_norms = {_norm(v) for v in names if _norm(v)}
    slug_norms = {_norm(v) for v in slugs if _norm(v)}
    return name_norms == {evidence["name"]} and slug_norms == {evidence["slug"]}


def _stable_symbol_with_evidence(v2a, symbol: str, name: str) -> bool:
    if _ORIGINAL_STABLE_SYMBOL(v2a, symbol, name):
        return True
    allowed_names = EVIDENCE_BACKED_PIT_STABLES.get(str(symbol), set())
    return bool(allowed_names and _norm(name) in allowed_names)


def _identity_audit_with_single_char_evidence(snapshots, coinlist, v2a):
    identity = _ORIGINAL_IDENTITY_AUDIT(snapshots, coinlist, v2a)
    for symbol in EVIDENCE_BACKED_SINGLE_CHAR:
        mask = identity["symbol"].astype(str) == symbol
        if not bool(mask.any()):
            continue
        names = sorted(set(snapshots.loc[snapshots["symbol"].astype(str) == symbol, "name"].astype(str)))
        slugs = []
        if "cmc_slug" in snapshots.columns:
            slugs = sorted({str(v) for v in snapshots.loc[snapshots["symbol"].astype(str) == symbol, "cmc_slug"].dropna()})
        if _single_char_evidence_ok(symbol, names, slugs):
            identity.loc[mask, "exchange_identity_ok"] = True
            identity.loc[mask, "identity_confidence"] = "CURATED_PIT_SINGLE_CHAR"
    return identity


def _bounded_relabel(history: pd.DataFrame, target: str, source: str, start=None, end_exclusive=None) -> pd.DataFrame:
    if history is None or history.empty:
        return _empty()
    out = history.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
    if start is not None:
        out = out[out["date"] >= pd.Timestamp(start)]
    if end_exclusive is not None:
        out = out[out["date"] < pd.Timestamp(end_exclusive)]
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(pd.to_numeric(out["close_usd"], errors="coerce") > 0) & (pd.to_numeric(out["volume_usd"], errors="coerce") >= 0)]
    out["symbol"] = target
    out["source"] = source
    return out.drop_duplicates("date", keep="last").sort_values("date")[COLS]


def _recover_borg(session, row) -> tuple[pd.DataFrame, str, str]:
    if pd.Timestamp(row.last_snapshot) >= BORG_MIGRATION_DATE:
        return _empty(), "", "BLOCKED_SNAPSHOT_CROSSES_CHSB_BORG_MIGRATION"
    history, url, status = staged.runner.cdd_multi.fetch_symbol(
        session, "CHSB", pd.Timestamp(row.first_snapshot), pd.Timestamp(row.last_snapshot)
    )
    if status != "PASS" or history.empty:
        return _empty(), url, status
    source = "legacy_chsb_pre_borg_migration__" + str(history["source"].iloc[0])
    out = _bounded_relabel(history, "BORG", source, end_exclusive=BORG_MIGRATION_DATE)
    return out, url, "PASS" if len(out) >= 2 else "NO_BOUNDED_CHSB_HISTORY"


def _recover_bttold(session, row) -> tuple[pd.DataFrame, str, str]:
    if pd.Timestamp(row.first_snapshot) >= BTT_REDENOMINATION_DATE:
        return _empty(), "", "BLOCKED_SNAPSHOT_AFTER_BTT_REDENOMINATION"
    history, url, status = staged.runner.cdd_multi.fetch_symbol(
        session, "BTT", pd.Timestamp(row.first_snapshot), min(pd.Timestamp(row.last_snapshot), BTT_REDENOMINATION_DATE - pd.Timedelta(days=1))
    )
    if status != "PASS" or history.empty:
        return _empty(), url, status
    source = "legacy_btt_pre_redenomination__" + str(history["source"].iloc[0])
    out = _bounded_relabel(history, "BTTOLD", source, end_exclusive=BTT_REDENOMINATION_DATE)
    return out, url, "PASS" if len(out) >= 2 else "NO_BOUNDED_LEGACY_BTT_HISTORY"


def _recover_rev(session, row) -> tuple[pd.DataFrame, str, str]:
    if pd.Timestamp(row.first_snapshot) < REV_RENAME_COMPLETE_DATE:
        return _empty(), "", "BLOCKED_SNAPSHOT_PREDATES_R_REV_COMPLETION"
    history, status = staged.runner.exchange_history.fetch_kucoin(session, "R")
    if status != "PASS" or history.empty:
        return _empty(), "https://api.kucoin.com/api/v1/market/candles?symbol=R-USDT", status
    out = _bounded_relabel(
        history,
        "REV",
        "kucoin_legacy_api_r_usdt_post_rev_swap",
        start=REV_RENAME_COMPLETE_DATE,
    )
    return out, "https://api.kucoin.com/api/v1/market/candles?symbol=R-USDT", "PASS" if len(out) >= 2 else "NO_POST_SWAP_KUCOIN_R_HISTORY"


def _mexc_request(session, params: dict, tries: int = 4):
    url = "https://api.mexc.com/api/v3/klines"
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=30)
            if response.status_code == 200:
                return response
            if response.status_code in {429, 500, 502, 503, 504}:
                time.sleep(0.5 + attempt)
                continue
            return None
        except Exception:
            if attempt + 1 >= tries:
                return None
            time.sleep(0.5 + attempt)
    return None


def _recover_mx(session, row) -> tuple[pd.DataFrame, str, str]:
    if pd.Timestamp(row.first_snapshot) < MEXC_HISTORY_START:
        return _empty(), "", "BLOCKED_MX_SNAPSHOT_PREDATES_MEXC_HISTORY_CONTRACT"
    url = "https://api.mexc.com/api/v3/klines"
    rows = []
    cursor = max(MEXC_HISTORY_START, pd.Timestamp(row.first_snapshot) - pd.Timedelta(days=200))
    stop_all = min(MEXC_END, pd.Timestamp(row.last_snapshot) + pd.Timedelta(days=35))
    while cursor <= stop_all:
        stop = min(cursor + pd.Timedelta(days=999), stop_all)
        response = _mexc_request(session, {
            "symbol": "MXUSDT",
            "interval": "1d",
            "startTime": int(cursor.tz_localize("UTC").timestamp() * 1000),
            "endTime": int((stop + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)).tz_localize("UTC").timestamp() * 1000),
            "limit": 1000,
        })
        if response is None:
            break
        try:
            data = response.json()
        except Exception:
            data = []
        if not isinstance(data, list):
            break
        for rec in data:
            if not isinstance(rec, list) or len(rec) < 8:
                continue
            rows.append((rec[0], rec[4], rec[7]))
        cursor = stop + pd.Timedelta(days=1)
        time.sleep(0.02)
    if not rows:
        return _empty(), url, "NO_MEXC_MXUSDT_HISTORY"
    raw = pd.DataFrame(rows, columns=["time_ms", "close_usd", "volume_usd"])
    raw["date"] = pd.to_datetime(pd.to_numeric(raw["time_ms"], errors="coerce"), unit="ms", utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    raw["symbol"] = "MX"
    raw["source"] = "mexc_spot_mxusdt"
    out = _bounded_relabel(raw, "MX", "mexc_spot_mxusdt", start=MEXC_HISTORY_START)
    return out, url, "PASS" if len(out) >= 2 else "NO_MEXC_MXUSDT_HISTORY"


def _recover_residuals(session, identity: pd.DataFrame, outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    fetchers = {
        "BORG": _recover_borg,
        "BTTOLD": _recover_bttold,
        "REV": _recover_rev,
        "MX": _recover_mx,
    }
    frames = []
    coverage = []
    indexed = identity.set_index("symbol", drop=False)
    for symbol in RESIDUAL_SYMBOLS:
        if symbol not in indexed.index:
            coverage.append({"symbol": symbol, "status": "NOT_IN_PIT", "rows": 0, "first_date": None, "last_date": None, "source": "", "source_url": ""})
            continue
        row = indexed.loc[symbol]
        if isinstance(row, pd.DataFrame):
            coverage.append({"symbol": symbol, "status": "BLOCKED_DUPLICATE_IDENTITY_ROWS", "rows": 0, "first_date": None, "last_date": None, "source": "", "source_url": ""})
            continue
        if not bool(row.get("exchange_identity_ok", False)):
            coverage.append({"symbol": symbol, "status": "BLOCKED_IDENTITY", "rows": 0, "first_date": None, "last_date": None, "source": "", "source_url": ""})
            continue
        try:
            history, url, status = fetchers[symbol](session, row)
        except Exception as exc:
            history, url, status = _empty(), "", f"ERROR_{type(exc).__name__}"
        if not history.empty:
            frames.append(history)
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(history),
            "first_date": history["date"].min() if not history.empty else None,
            "last_date": history["date"].max() if not history.empty else None,
            "source": str(history["source"].iloc[0]) if not history.empty else "",
            "source_url": url,
        })
        print(f"RESIDUAL_RECOVERY {symbol} rows={len(history)} status={status}", flush=True)
    master = pd.concat(frames, ignore_index=True) if frames else _empty()
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "RESIDUAL_RECOVERY_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "RESIDUAL_RECOVERY_COVERAGE.csv", index=False)
    policy = {
        "schema": "gate_btc.pit_residual_recovery.v1",
        "status": "RESEARCH_ONLY_BOUNDED_LEGACY_LABEL_RECOVERY",
        "symbols": list(RESIDUAL_SYMBOLS),
        "borg_migration_date_exclusive": str(BORG_MIGRATION_DATE.date()),
        "btt_redenomination_date_exclusive": str(BTT_REDENOMINATION_DATE.date()),
        "rev_post_swap_start_inclusive": str(REV_RENAME_COMPLETE_DATE.date()),
        "mexc_history_start_inclusive": str(MEXC_HISTORY_START.date()),
        "cross_boundary_stitching": False,
        "synthetic_conversion": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    (outdir / "RESIDUAL_RECOVERY_POLICY.json").write_text(json.dumps(policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return master, cov


def _collect_histories_with_residual_recovery(session, identity, outdir: Path):
    master, cov = _ORIGINAL_COLLECT_HISTORIES(session, identity, outdir)
    residual_master, residual_cov = _recover_residuals(session, identity, outdir)
    if residual_master.empty:
        return master, cov

    combined = master.copy()
    cov = cov.copy()
    if "residual_recovery_rows" not in cov.columns:
        cov["residual_recovery_rows"] = 0

    for row in residual_cov.itertuples(index=False):
        symbol = str(row.symbol)
        if int(getattr(row, "rows", 0) or 0) < 2:
            continue
        identity_rows = identity[identity["symbol"].astype(str) == symbol]
        if len(identity_rows) != 1:
            continue
        ir = identity_rows.iloc[0]
        existing = staged.runner._slice(combined, symbol)
        residual = staged.runner._slice(residual_master, symbol)
        best, source = staged.runner._choose_source(
            [existing, residual], pd.Timestamp(ir["first_snapshot"]), pd.Timestamp(ir["last_snapshot"])
        )
        if best.empty or source != str(residual["source"].iloc[0]):
            continue
        combined = combined[combined["symbol"].astype(str) != symbol]
        combined = pd.concat([combined, best[COLS]], ignore_index=True)
        mask = cov["symbol"].astype(str) == symbol
        if not bool(mask.any()):
            continue
        cov.loc[mask, "status"] = "PASS"
        cov.loc[mask, "rows"] = len(best)
        cov.loc[mask, "first_date"] = best["date"].min()
        cov.loc[mask, "last_date"] = best["date"].max()
        cov.loc[mask, "selected_source"] = source
        cov.loc[mask, "residual_recovery_rows"] = len(best)
        imask = identity["symbol"].astype(str) == symbol
        identity.loc[imask, "history_usable"] = True
        identity.loc[imask, "history_source"] = source
        identity.loc[imask, "history_rows"] = len(best)

    combined = combined.sort_values(["symbol", "date"]).drop_duplicates(["symbol", "date"], keep="last")
    combined.to_csv(outdir / "CASCADE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CASCADE_COVERAGE.csv", index=False)
    identity.to_csv(outdir / "IDENTITY_AUDIT.csv", index=False)

    summary_path = outdir / "SOURCE_CASCADE_SUMMARY.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    summary["history_pass"] = int((cov["status"] == "PASS").sum())
    counts = cov.loc[(cov["status"] == "PASS") & cov["selected_source"].fillna("").ne(""), "selected_source"].astype(str).value_counts().to_dict()
    summary["selected_sources"] = {str(k): int(v) for k, v in sorted(counts.items())}
    summary["residual_recovery_candidates"] = list(RESIDUAL_SYMBOLS)
    summary["residual_recovery_pass"] = int((residual_cov["status"] == "PASS").sum())
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SOURCE_CASCADE_AFTER_RESIDUAL=" + json.dumps(summary, sort_keys=True), flush=True)
    return combined, cov


def apply_continuity_evidence() -> None:
    for symbol, aliases in EVIDENCE_BACKED_CONTINUITIES.items():
        staged.runner.definitive.KNOWN_CONTINUITIES.setdefault(symbol, set()).update(aliases)
    staged.runner._cascade_identity_audit = _identity_audit_with_single_char_evidence
    staged.runner.definitive.stable_symbol = _stable_symbol_with_evidence
    staged.runner._cascade_collect_histories = _collect_histories_with_residual_recovery


def main() -> int:
    apply_continuity_evidence()
    return staged.main()


if __name__ == "__main__":
    raise SystemExit(main())
