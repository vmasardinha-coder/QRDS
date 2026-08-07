#!/usr/bin/env python3
"""Run the definitive public PIT study with CMC rankings + Coin Metrics Community history."""
from __future__ import annotations

import requests

import gate_btc_cmc_pit_collector as cmc_collector
import gate_btc_cmc_pit_parser as cmc_parser
import gate_btc_coinmetrics_pit_history as cm_history
import gate_btc_survivorship_definitive_pit as definitive

_ORIGINAL_HTTP_GET = definitive.http_get
_ORIGINAL_RUN_ALPHA = definitive.run_alpha
_ORIGINAL_WRITE_TEXT = definitive.write_text
_CM_REFERENCE = None
_CM_CATALOG = None


class _StubCoinListResponse:
    def json(self):
        return {"Data": {}}


def _http_get_without_cryptocompare_coinlist(session, url, params=None, tries=6):
    if "min-api.cryptocompare.com/data/all/coinlist" in str(url):
        return _StubCoinListResponse()
    return _ORIGINAL_HTTP_GET(session, url, params, tries)


def _cm_identity_audit(snapshots, _unused_coinlist, _v2a):
    global _CM_REFERENCE, _CM_CATALOG
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})
    _CM_REFERENCE = cm_history.asset_reference(session)
    _CM_CATALOG = cm_history.metric_catalog(session)
    return cm_history.resolve_cmc_to_cm(snapshots, _CM_REFERENCE, _CM_CATALOG)


def _cm_collect_histories(session, identity, outdir):
    if _CM_REFERENCE is not None:
        _CM_REFERENCE.to_csv(outdir / "COINMETRICS_ASSET_REFERENCE.csv", index=False)
    return cm_history.collect_histories(session, identity, outdir)


def _run_alpha_cm(alpha_tool, weekly, unresolved):
    result = _ORIGINAL_RUN_ALPHA(alpha_tool, weekly, unresolved)
    provenance = result.get("provenance")
    if isinstance(provenance, dict):
        provenance["external_data_basis"] = "CMC_MONTH_END_TOP150_PLUS_COINMETRICS_COMMUNITY_DAILY"
        provenance["price_metric"] = cm_history.PRICE_METRIC
        provenance["volume_metric"] = cm_history.VOLUME_METRIC
    return result


def _write_text_cm(outdir, manifest, alpha, survivor_alpha, identity, coverage):
    _ORIGINAL_WRITE_TEXT(outdir, manifest, alpha, survivor_alpha, identity, coverage)
    method = outdir / "METODOLOGIA.md"
    if method.is_file():
        text = method.read_text(encoding="utf-8")
        text = text.replace(
            "Daily price/volume source: CryptoCompare CCCAGG, identity-audited by symbol/name history.",
            "Daily price/volume source: Coin Metrics Community API using PriceUSD and volume_reported_spot_usd_1d, identity-audited against Coin Metrics reference-data/assets.",
        )
        method.write_text(text, encoding="utf-8")
    executive = outdir / "EXECUTIVE_SUMMARY.txt"
    if executive.is_file():
        text = executive.read_text(encoding="utf-8").replace("CC_HISTORY_PASS=", "COINMETRICS_HISTORY_PASS=")
        executive.write_text(text, encoding="utf-8")


def main() -> int:
    definitive.parse_cmc_html = cmc_parser.parse_cmc_html
    definitive.collect_snapshots = cmc_collector.collect_snapshots
    definitive.http_get = _http_get_without_cryptocompare_coinlist
    definitive.identity_audit = _cm_identity_audit
    definitive.collect_histories = _cm_collect_histories
    definitive.run_alpha = _run_alpha_cm
    definitive.write_text = _write_text_cm
    return definitive.main()


if __name__ == "__main__":
    raise SystemExit(main())
