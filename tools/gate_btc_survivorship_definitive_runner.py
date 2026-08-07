#!/usr/bin/env python3
"""Run the definitive public PIT study with a public OHLCV source cascade."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import requests

import gate_btc_cmc_pit_collector as cmc_collector
import gate_btc_cmc_pit_parser as cmc_parser
import gate_btc_coinmetrics_pit_history as cm_history
import gate_btc_cdd_binance_pit_history as cdd_history
import gate_btc_exchange_pit_history as exchange_history
import gate_btc_survivorship_definitive_pit as definitive

_ORIGINAL_HTTP_GET = definitive.http_get
_ORIGINAL_WRITE_TEXT = definitive.write_text
_ORIGINAL_RUN_ALPHA = definitive.run_alpha
_ORIGINAL_DIRECT = definitive.direct_delta_fits
_CM_REFERENCE = None
_CM_CATALOG = None


class _StubCoinListResponse:
    def json(self):
        return {"Data": {}}


def _http_get_without_cryptocompare_coinlist(session, url, params=None, tries=6):
    if "min-api.cryptocompare.com/data/all/coinlist" in str(url):
        return _StubCoinListResponse()
    return _ORIGINAL_HTTP_GET(session, url, params, tries)


def _norm(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _continuity_ok(symbol: str, names: list[str]) -> bool:
    norms = sorted(set(_norm(x) for x in names if _norm(x)))
    if not norms:
        return False
    if len(norms) == 1:
        return True
    aliases = {_norm(x) for x in definitive.KNOWN_CONTINUITIES.get(symbol, set()) if _norm(x)}
    if not aliases:
        return False
    return all(any(n == a or n in a or a in n for a in aliases) for n in norms)


def _cascade_identity_audit(snapshots, _unused_coinlist, v2a):
    global _CM_REFERENCE, _CM_CATALOG
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})
    _CM_REFERENCE = cm_history.asset_reference(session)
    _CM_CATALOG = cm_history.metric_catalog(session)
    identity = cm_history.resolve_cmc_to_cm(snapshots, _CM_REFERENCE, _CM_CATALOG).copy()
    name_map = snapshots.groupby("symbol")["name"].apply(lambda x: sorted(set(x.astype(str)))).to_dict()
    identity["exchange_identity_ok"] = [
        bool(
            not (str(s).startswith("U") and len(str(s)) == 9)
            and v2a.standard_ticker(str(s))
            and _continuity_ok(str(s), name_map.get(str(s), []))
        )
        for s in identity["symbol"]
    ]
    identity["history_source"] = identity.apply(
        lambda r: "coinmetrics_community" if bool(r.get("history_usable")) else "", axis=1
    )
    identity["history_rows"] = 0
    return identity


def _clean(frame: pd.DataFrame, source_default: str = "") -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date","symbol","close_usd","volume_usd","source"])
    out = frame.dropna(subset=["date","close_usd","volume_usd"]).copy()
    if "source" not in out:
        out["source"] = source_default
    return out.sort_values("date").drop_duplicates("date", keep="last")


def _choose_source(frames: list[pd.DataFrame], first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> tuple[pd.DataFrame, str]:
    candidates = []
    membership_end = min(pd.Timestamp("2026-08-06"), pd.Timestamp(last_snapshot) + pd.Timedelta(days=35))
    membership_start = pd.Timestamp(first_snapshot)
    for frame in frames:
        f = _clean(frame)
        if f.empty:
            continue
        member_rows = int(((f["date"] >= membership_start) & (f["date"] <= membership_end)).sum())
        pre_rows = int(((f["date"] < membership_start) & (f["date"] >= membership_start - pd.Timedelta(days=200))).sum())
        span_days = int((f["date"].max() - f["date"].min()).days) if len(f) > 1 else 0
        source = str(f["source"].iloc[0])
        # Prioritize actual PIT membership coverage, then factor lookback support,
        # then total continuity. No source stitching inside one symbol.
        score = (member_rows, pre_rows, len(f), span_days, source.startswith("cryptodatadownload_binance_"))
        candidates.append((score, f, source))
    if not candidates:
        return _clean(pd.DataFrame()), ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, best, source = candidates[0]
    return best, source


def _cascade_collect_histories(session, identity, outdir: Path):
    if _CM_REFERENCE is not None:
        _CM_REFERENCE.to_csv(outdir / "COINMETRICS_ASSET_REFERENCE.csv", index=False)
    cm_master, _ = cm_history.collect_histories(session, identity, outdir)
    candidates = identity.loc[identity["exchange_identity_ok"], "symbol"].astype(str).tolist()
    cdd_master, _ = cdd_history.collect(session, candidates, outdir)

    # First pass: identify names still lacking usable coverage over their PIT membership.
    need_extra = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        cm = cm_master[cm_master["symbol"] == symbol].copy() if not cm_master.empty else pd.DataFrame()
        cdd = cdd_master[cdd_master["symbol"] == symbol].copy() if not cdd_master.empty else pd.DataFrame()
        best, _ = _choose_source([cm, cdd], pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot))
        if best.empty:
            need_extra.append(symbol)
            continue
        membership = best[(best["date"] >= pd.Timestamp(r.first_snapshot)) & (best["date"] <= min(pd.Timestamp("2026-08-06"), pd.Timestamp(r.last_snapshot) + pd.Timedelta(days=35)))]
        if membership.empty or membership["date"].min() > pd.Timestamp(r.first_snapshot) + pd.Timedelta(days=7):
            need_extra.append(symbol)

    print(f"CASCADE_EXTRA_CANDIDATES={len(need_extra)}", flush=True)
    gate_master, _ = exchange_history.collect_source(session, need_extra, outdir, "gateio", exchange_history.fetch_gate)
    kucoin_master, _ = exchange_history.collect_source(session, need_extra, outdir, "kucoin", exchange_history.fetch_kucoin)

    selected = []
    coverage = []
    symbols = identity["symbol"].astype(str).tolist()
    source_counts = {}
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        cm = cm_master[cm_master["symbol"] == symbol].copy() if not cm_master.empty else pd.DataFrame()
        cdd = cdd_master[cdd_master["symbol"] == symbol].copy() if not cdd_master.empty else pd.DataFrame()
        gate = gate_master[gate_master["symbol"] == symbol].copy() if not gate_master.empty else pd.DataFrame()
        kucoin = kucoin_master[kucoin_master["symbol"] == symbol].copy() if not kucoin_master.empty else pd.DataFrame()
        best, source = _choose_source([cm, cdd, gate, kucoin], pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot))
        if not best.empty:
            best = best.copy()
            best["symbol"] = symbol
            selected.append(best[["date","symbol","close_usd","volume_usd","source"]])
            source_counts[source] = source_counts.get(source, 0) + 1
        status = "PASS" if len(best) >= 2 else "NO_USABLE_HISTORY"
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(best),
            "first_date": best["date"].min() if not best.empty else None,
            "last_date": best["date"].max() if not best.empty else None,
            "selected_source": source,
            "coinmetrics_rows": len(cm),
            "cdd_binance_rows": len(cdd),
            "gateio_rows": len(gate),
            "kucoin_rows": len(kucoin),
        })
        mask = identity["symbol"].astype(str) == symbol
        identity.loc[mask, "history_usable"] = status == "PASS"
        identity.loc[mask, "history_source"] = source
        identity.loc[mask, "history_rows"] = len(best)

    master = pd.concat(selected, ignore_index=True) if selected else pd.DataFrame(columns=["date","symbol","close_usd","volume_usd","source"])
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "CASCADE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CASCADE_COVERAGE.csv", index=False)
    identity.to_csv(outdir / "IDENTITY_AUDIT.csv", index=False)
    summary = {
        "symbols_total": len(symbols),
        "history_pass": int((cov["status"] == "PASS").sum()),
        "extra_candidates": len(need_extra),
        "selected_sources": source_counts,
    }
    (outdir / "SOURCE_CASCADE_SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SOURCE_CASCADE=" + json.dumps(summary, sort_keys=True), flush=True)
    return master, cov


def _safe_run_alpha(alpha_tool, weekly, unresolved):
    baskets = set(weekly["basket"].astype(str)) if not weekly.empty and "basket" in weekly else set()
    required = {"UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"}
    if not required.issubset(baskets):
        return {
            "status": "PARTIAL_COVERAGE_RESEARCH_ONLY",
            "coverage": {"common_weeks": 0, "min_ratio": 0.0},
            "results": {},
            "provenance": {
                "external_data_basis": "CMC_MONTH_END_TOP150_PLUS_PUBLIC_SOURCE_CASCADE",
                "execution_convention": "STRICT_NEXT_BAR_EXECUTION",
                "point_in_time_universe": True,
                "point_in_time_selection_recomputed": True,
                "provisional_or_unresolved_censoring_remaining": True,
                "engine_feed": False,
                "methodology_changes": 0,
                "orders_generated": 0,
                "real_capital_used": 0,
            },
        }
    result = _ORIGINAL_RUN_ALPHA(alpha_tool, weekly, unresolved)
    provenance = result.get("provenance")
    if isinstance(provenance, dict):
        provenance["external_data_basis"] = "CMC_MONTH_END_TOP150_PLUS_PUBLIC_SOURCE_CASCADE"
        provenance["source_priority"] = "one continuous public source per symbol; maximize PIT membership coverage"
    return result


def _safe_direct(alpha_tool, weekly):
    baskets = set(weekly["basket"].astype(str)) if not weekly.empty and "basket" in weekly else set()
    required = {"UNFILTERED_PIT", "SELECTED_MODERADA_PIT", "SELECTED_ULTRA_PIT"}
    return _ORIGINAL_DIRECT(alpha_tool, weekly) if required.issubset(baskets) else {}


def _write_text_cascade(outdir, manifest, alpha, survivor_alpha, identity, coverage):
    _ORIGINAL_WRITE_TEXT(outdir, manifest, alpha, survivor_alpha, identity, coverage)
    method = outdir / "METODOLOGIA.md"
    if method.is_file():
        text = method.read_text(encoding="utf-8")
        text = text.replace(
            "Daily price/volume source: CryptoCompare CCCAGG, identity-audited by symbol/name history.",
            "Daily price/volume sources: public one-source-per-symbol cascade. Layers: CryptoDataDownload/Binance stable-quote daily OHLCV, Coin Metrics Community PriceUSD + reported spot USD volume, Gate.io USDT daily candles, and KuCoin USDT daily candles. Missing history is never synthesized.",
        )
        method.write_text(text, encoding="utf-8")
    executive = outdir / "EXECUTIVE_SUMMARY.txt"
    if executive.is_file():
        text = executive.read_text(encoding="utf-8").replace("CC_HISTORY_PASS=", "CASCADE_HISTORY_PASS=")
        executive.write_text(text, encoding="utf-8")


def main() -> int:
    definitive.parse_cmc_html = cmc_parser.parse_cmc_html
    definitive.collect_snapshots = cmc_collector.collect_snapshots
    definitive.http_get = _http_get_without_cryptocompare_coinlist
    definitive.identity_audit = _cascade_identity_audit
    definitive.collect_histories = _cascade_collect_histories
    definitive.run_alpha = _safe_run_alpha
    definitive.direct_delta_fits = _safe_direct
    definitive.write_text = _write_text_cascade
    return definitive.main()


if __name__ == "__main__":
    raise SystemExit(main())
