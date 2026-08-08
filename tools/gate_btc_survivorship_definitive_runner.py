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
import gate_btc_cdd_multi_exchange_pit_history as cdd_multi
import gate_btc_exchange_pit_history as exchange_history
import gate_btc_bybit_okx_pit_history as byok_history
import gate_btc_bybit_archive_pit_history as bybit_archive
import gate_btc_binance_vision_pit_history as binance_vision
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


def _continuity_ok(symbol: str, names: list[str], slugs: list[str] | None = None) -> bool:
    norms = sorted(set(_norm(x) for x in names if _norm(x)))
    slug_norms = sorted(set(_norm(x) for x in (slugs or []) if _norm(x)))
    if not norms:
        return False
    if len(norms) == 1:
        return True
    # A unique historical CMC currency slug is a stronger lineage key than the
    # rendered display name. It permits benign renames while ticker reuse remains
    # fail-closed because reused assets carry distinct slugs. No price/factor
    # information participates in this decision.
    if len(slug_norms) == 1:
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
    if "cmc_slug" in snapshots.columns:
        slug_map = snapshots.groupby("symbol")["cmc_slug"].apply(
            lambda x: sorted({str(v) for v in x.dropna() if _norm(v)})
        ).to_dict()
    else:
        slug_map = {}
    identity["cmc_slugs"] = identity["symbol"].map(lambda s: ";".join(slug_map.get(str(s), [])))
    identity["exchange_identity_ok"] = [
        bool(
            not (str(s).startswith("U") and len(str(s)) == 9)
            and v2a.standard_ticker(str(s))
            and _continuity_ok(str(s), name_map.get(str(s), []), slug_map.get(str(s), []))
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
        score = (
            member_rows,
            pre_rows,
            len(f),
            span_days,
            source.startswith("cryptodatadownload_binance_"),
        )
        candidates.append((score, f, source))
    if not candidates:
        return _clean(pd.DataFrame()), ""
    candidates.sort(key=lambda x: x[0], reverse=True)
    _, best, source = candidates[0]
    return best, source


def _needs_extra(best: pd.DataFrame, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> bool:
    if best.empty:
        return True
    start = pd.Timestamp(first_snapshot)
    end = min(pd.Timestamp("2026-08-06"), pd.Timestamp(last_snapshot) + pd.Timedelta(days=35))
    membership = best[(best["date"] >= start) & (best["date"] <= end)]
    return bool(membership.empty or membership["date"].min() > start + pd.Timedelta(days=7))


def _slice(master: pd.DataFrame, symbol: str) -> pd.DataFrame:
    return master[master["symbol"] == symbol].copy() if master is not None and not master.empty else pd.DataFrame()


def _collect_cryptocompare_direct_usd(session, symbols: list[str], outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Final public recovery layer using direct CCCAGG USD history only.

    The underlying canonical helper sends tryConversion=false, so a BTC/other
    synthetic conversion path is never admitted. This remains one continuous
    source per symbol and missing rows are never filled or converted to zero.
    """
    frames = []
    coverage = []
    unique = sorted(set(symbols))
    for position, symbol in enumerate(unique, 1):
        try:
            history = definitive.collect_cc_history(session, symbol)
            if not history.empty:
                history = history.copy()
                history["source"] = "cryptocompare_cccagg_direct_usd"
            status = "PASS" if len(history) >= 2 else "NO_DIRECT_USD_HISTORY"
        except Exception as exc:
            history = pd.DataFrame(columns=["date","symbol","close_usd","volume_usd","source"])
            status = f"ERROR:{type(exc).__name__}"
        if not history.empty:
            frames.append(history[["date","symbol","close_usd","volume_usd","source"]])
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(history),
            "first_date": history["date"].min() if not history.empty else None,
            "last_date": history["date"].max() if not history.empty else None,
            "source_url": "https://min-api.cryptocompare.com/data/v2/histoday",
            "exchange": "CCCAGG",
            "quote": "USD",
            "try_conversion": False,
        })
        print(f"CRYPTOCOMPARE {position}/{len(unique)} {symbol} rows={len(history)} {status}", flush=True)
    master = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["date","symbol","close_usd","volume_usd","source"])
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "CRYPTOCOMPARE_DIRECT_USD_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CRYPTOCOMPARE_DIRECT_USD_COVERAGE.csv", index=False)
    return master, cov


def _cascade_collect_histories(session, identity, outdir: Path):
    if _CM_REFERENCE is not None:
        _CM_REFERENCE.to_csv(outdir / "COINMETRICS_ASSET_REFERENCE.csv", index=False)
    cm_master, _ = cm_history.collect_histories(session, identity, outdir)
    candidates = identity.loc[identity["exchange_identity_ok"], "symbol"].astype(str).tolist()
    cdd_master, _ = cdd_history.collect(session, candidates, outdir)

    need_extra = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        best, _ = _choose_source(
            [_slice(cm_master, symbol), _slice(cdd_master, symbol)],
            pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot),
        )
        if _needs_extra(best, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot)):
            need_extra.append(symbol)

    print(f"CASCADE_EXTRA_CANDIDATES={len(need_extra)}", flush=True)
    gate_master, _ = exchange_history.collect_source(session, need_extra, outdir, "gateio", exchange_history.fetch_gate)
    kucoin_master, _ = exchange_history.collect_source(session, need_extra, outdir, "kucoin", exchange_history.fetch_kucoin)
    bybit_master, _ = byok_history.collect_source(session, need_extra, outdir, "bybit", byok_history.fetch_bybit)
    okx_master, _ = byok_history.collect_source(session, need_extra, outdir, "okx", byok_history.fetch_okx)

    need_archive = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        best, _ = _choose_source(
            [
                _slice(cm_master, symbol),
                _slice(cdd_master, symbol),
                _slice(gate_master, symbol),
                _slice(kucoin_master, symbol),
                _slice(bybit_master, symbol),
                _slice(okx_master, symbol),
            ],
            pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot),
        )
        if _needs_extra(best, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot)):
            need_archive.append(symbol)
    print(f"BINANCE_VISION_ARCHIVE_CANDIDATES={len(need_archive)}", flush=True)
    vision_master, _ = binance_vision.collect(session, identity, need_archive, outdir)

    need_cdd_multi = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        best, _ = _choose_source(
            [
                _slice(cm_master, symbol),
                _slice(cdd_master, symbol),
                _slice(gate_master, symbol),
                _slice(kucoin_master, symbol),
                _slice(bybit_master, symbol),
                _slice(okx_master, symbol),
                _slice(vision_master, symbol),
            ],
            pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot),
        )
        if _needs_extra(best, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot)):
            need_cdd_multi.append(symbol)
    print(f"CDD_MULTI_EXCHANGE_CANDIDATES={len(need_cdd_multi)}", flush=True)
    cdd_multi_master, _ = cdd_multi.collect(session, identity, need_cdd_multi, outdir)

    need_bybit_archive = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        best, _ = _choose_source(
            [
                _slice(cm_master, symbol),
                _slice(cdd_master, symbol),
                _slice(gate_master, symbol),
                _slice(kucoin_master, symbol),
                _slice(bybit_master, symbol),
                _slice(okx_master, symbol),
                _slice(vision_master, symbol),
                _slice(cdd_multi_master, symbol),
            ],
            pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot),
        )
        if _needs_extra(best, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot)):
            need_bybit_archive.append(symbol)
    print(f"BYBIT_PUBLIC_ARCHIVE_CANDIDATES={len(need_bybit_archive)}", flush=True)
    bybit_archive_master, _ = bybit_archive.collect(session, identity, need_bybit_archive, outdir)

    need_cryptocompare = []
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        if not bool(getattr(r, "exchange_identity_ok", False)):
            continue
        best, _ = _choose_source(
            [
                _slice(cm_master, symbol),
                _slice(cdd_master, symbol),
                _slice(gate_master, symbol),
                _slice(kucoin_master, symbol),
                _slice(bybit_master, symbol),
                _slice(okx_master, symbol),
                _slice(vision_master, symbol),
                _slice(cdd_multi_master, symbol),
                _slice(bybit_archive_master, symbol),
            ],
            pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot),
        )
        if _needs_extra(best, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot)):
            need_cryptocompare.append(symbol)
    print(f"CRYPTOCOMPARE_DIRECT_USD_CANDIDATES={len(need_cryptocompare)}", flush=True)
    cryptocompare_master, _ = _collect_cryptocompare_direct_usd(session, need_cryptocompare, outdir)

    selected = []
    coverage = []
    symbols = identity["symbol"].astype(str).tolist()
    source_counts: dict[str, int] = {}
    for r in identity.itertuples(index=False):
        symbol = str(r.symbol)
        frames = [
            _slice(cm_master, symbol),
            _slice(cdd_master, symbol),
            _slice(gate_master, symbol),
            _slice(kucoin_master, symbol),
            _slice(bybit_master, symbol),
            _slice(okx_master, symbol),
            _slice(vision_master, symbol),
            _slice(cdd_multi_master, symbol),
            _slice(bybit_archive_master, symbol),
            _slice(cryptocompare_master, symbol),
        ]
        best, source = _choose_source(frames, pd.Timestamp(r.first_snapshot), pd.Timestamp(r.last_snapshot))
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
            "coinmetrics_rows": len(frames[0]),
            "cdd_binance_rows": len(frames[1]),
            "gateio_rows": len(frames[2]),
            "kucoin_rows": len(frames[3]),
            "bybit_rows": len(frames[4]),
            "okx_rows": len(frames[5]),
            "binance_vision_rows": len(frames[6]),
            "cdd_multi_rows": len(frames[7]),
            "bybit_archive_rows": len(frames[8]),
            "cryptocompare_direct_usd_rows": len(frames[9]),
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
        "binance_vision_archive_candidates": len(need_archive),
        "cdd_multi_exchange_candidates": len(need_cdd_multi),
        "bybit_public_archive_candidates": len(need_bybit_archive),
        "cryptocompare_direct_usd_candidates": len(need_cryptocompare),
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
            "Daily price/volume sources: public one-source-per-symbol cascade. Layers: CryptoDataDownload/Binance stable-quote daily OHLCV, Coin Metrics Community PriceUSD + reported spot USD volume, Gate.io USDT, KuCoin USDT, Bybit spot USDT, OKX spot USDT, official Binance Data Vision spot archives with SHA-256 verification, CryptoDataDownload USD-like daily archives across Bitfinex/Bitstamp/Coinbase/Gemini/Bittrex/Poloniex/CEX.io, Bybit public monthly Spot trade archives aggregated deterministically to daily bars with per-archive SHA-256, then CryptoCompare CCCAGG direct USD daily history with tryConversion=false. Missing history is never synthesized and venues/quotes are never stitched within a symbol.",
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
