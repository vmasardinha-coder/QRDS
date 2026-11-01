"""Read-only spot market coverage for admitted Dynamics targets.

Explicit scanner bindings are candidates, never a venue/account selection.
Metadata is not a price, an executable protocol or an economic observation.
"""
from __future__ import annotations

import copy
import hashlib

from tools import gate_btc_dynamics_spot_accounting as book
from tools import gate_btc_dynamics_target_intake as intake

URLS = {
    "https://api.binance.com/api/v3/exchangeInfo",
    "https://data-api.binance.vision/api/v3/exchangeInfo",
}


def _filters(row: dict) -> dict:
    items = row.get("filters")
    if not isinstance(items, list) or not items:
        raise ValueError("missing filters")
    out = {}
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get("filterType"), str):
            raise ValueError("invalid filter")
        key = item["filterType"]
        if key in out:
            raise ValueError("duplicate filter")
        out[key] = copy.deepcopy(item)
    for key, fields in {
        "LOT_SIZE": ("minQty", "maxQty", "stepSize"),
        "PRICE_FILTER": ("minPrice", "maxPrice", "tickSize"),
    }.items():
        if key not in out:
            raise ValueError("missing " + key)
        values = [book.number(out[key][f]) for f in fields]
        if any(v <= 0 for v in values) or values[1] < values[0]:
            raise ValueError("invalid " + key)
    if "MARKET_LOT_SIZE" in out:
        values = [book.number(out["MARKET_LOT_SIZE"][f])
                  for f in ("minQty", "maxQty", "stepSize")]
        if any(v < 0 for v in values) or values[1] <= 0 or values[1] < values[0]:
            raise ValueError("invalid MARKET_LOT_SIZE")
    notional = [key for key in ("MIN_NOTIONAL", "NOTIONAL") if key in out]
    if len(notional) != 1:
        raise ValueError("one explicit notional filter required")
    key = notional[0]
    item = out[key]
    if book.number(item["minNotional"]) <= 0:
        raise ValueError("invalid minimum notional")
    flags = ("applyToMarket",) if key == "MIN_NOTIONAL" else (
        "applyMinToMarket", "applyMaxToMarket")
    if any(type(item.get(f)) is not bool for f in flags):
        raise ValueError("explicit boolean market applicability required")
    if key == "NOTIONAL" and book.number(item["maxNotional"]) < book.number(item["minNotional"]):
        raise ValueError("invalid maximum notional")
    if type(item.get("avgPriceMins")) is not int or item["avgPriceMins"] < 0:
        raise ValueError("explicit notional reference window required")
    return out


def audit_markets(admission: dict, bindings: dict[str, str], *,
                  bindings_source_sha256: str, bindings_source_raw: bytes,
                  exchange_raw: bytes,
                  metadata_url: str, captured_at_utc: str, now_utc: str,
                  max_metadata_age_seconds: int, quote_currency: str) -> dict:
    """Report all missing markets without dropping/renormalizing target weights.

    The caller supplies exact scanner candidates and their source hash. A hash
    records provenance, not identity approval. No ticker concatenation, network
    discovery, alternate pair, alternate venue or synthetic cash is permitted.
    """
    weights = {p: intake.spot_weights(admission, p) for p in sorted(intake.SPOT)}
    required = {a for w in weights.values() for a, v in w.items()
                if a != "CASH" and book.number(v) > 0}
    book.check_hash(bindings_source_sha256)
    if hashlib.sha256(bindings_source_raw).hexdigest() != bindings_source_sha256:
        raise ValueError("scanner binding source hash mismatch")
    if not isinstance(bindings, dict) or set(bindings) - required:
        raise ValueError("bindings outside admitted spot targets")
    if any(not isinstance(v, str) or not v.strip() for v in bindings.values()):
        raise ValueError("explicit nonempty market bindings required")
    if len(set(bindings.values())) != len(bindings):
        raise ValueError("duplicate market binding")
    scanner = intake.table(bindings_source_raw, {"base", "binance_symbol", "binance_spot_available"})
    for asset, symbol in bindings.items():
        matches = [r for r in scanner if r["base"] == asset]
        if len(matches) != 1 or matches[0]["binance_symbol"] != symbol or matches[0]["binance_spot_available"] != "True":
            raise ValueError("binding not uniquely declared by scanner: " + asset)
    if not isinstance(quote_currency, str) or not quote_currency.strip():
        raise ValueError("explicit quote currency required")
    if metadata_url not in URLS:
        raise ValueError("unsupported metadata source")
    capture, now = book.timestamp(captured_at_utc), book.timestamp(now_utc)
    if capture < book.timestamp(admission["source_available_at_utc"]):
        raise ValueError("metadata predates target availability")
    if type(max_metadata_age_seconds) is not int or max_metadata_age_seconds <= 0:
        raise ValueError("positive integer metadata age bound required")
    if not 0 <= (now - capture).total_seconds() <= max_metadata_age_seconds:
        raise ValueError("future or stale metadata capture")
    metadata = intake.parse_json(exchange_raw)
    if not isinstance(metadata, dict):
        raise ValueError("metadata object required")
    rows = metadata.get("symbols")
    if not isinstance(rows, list):
        raise ValueError("missing symbols list")
    selected = {}
    wanted = set(bindings.values())
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("invalid symbol row")
        symbol = row.get("symbol")
        if symbol in wanted:
            if symbol in selected:
                raise ValueError("duplicate exchange symbol")
            selected[symbol] = row
    markets = {}
    for asset in sorted(required):
        symbol = bindings.get(asset)
        row = selected.get(symbol)
        reason = None
        filters = None
        if symbol is None:
            reason = "NO_EXPLICIT_SCANNER_BINDING"
        elif row is None:
            reason = "EXACT_MARKET_NOT_FOUND"
        elif row.get("baseAsset") != asset or row.get("quoteAsset") != quote_currency:
            reason = "BASE_OR_QUOTE_MISMATCH"
        elif row.get("status") != "TRADING" or row.get("isSpotTradingAllowed") is not True:
            reason = "SPOT_NOT_TRADING"
        elif not isinstance(row.get("orderTypes"), list) or "MARKET" not in row["orderTypes"]:
            reason = "MARKET_ORDER_TYPE_UNAVAILABLE"
        else:
            try:
                filters = _filters(row)
            except (ValueError, KeyError, TypeError, ArithmeticError) as exc:
                reason = "INVALID_FILTERS: " + str(exc)
        markets[asset] = {
            "candidate_market": symbol,
            "candidate_identity": "BINANCE:SPOT:" + symbol if symbol else None,
            "metadata_complete": reason is None, "blocked_reason": reason,
            "base_currency": asset, "quote_currency": quote_currency,
            "filters": filters, "identity_approved": False,
            "account_permission_verified": False,
        }
    profiles = {}
    for profile, target in weights.items():
        assets = sorted(a for a, v in target.items() if a != "CASH" and book.number(v) > 0)
        missing = [a for a in assets if not markets[a]["metadata_complete"]]
        profiles[profile] = {
            "target_weights": copy.deepcopy(target), "required_assets": assets,
            "missing_assets": missing, "market_metadata_complete": not missing,
            "executable": False,
        }
    result = {
        "schema": "gate_btc.dynamics_spot_market_audit.v1",
        "target_admission_sha256": admission["admission_sha256"],
        "target_available_at_utc": admission["source_available_at_utc"],
        "bindings_source_sha256": bindings_source_sha256,
        "metadata_sha256": hashlib.sha256(exchange_raw).hexdigest(),
        "metadata_url": metadata_url, "captured_at_utc": captured_at_utc,
        "audited_at_utc": now_utc, "max_metadata_age_seconds": max_metadata_age_seconds,
        "quote_currency": quote_currency, "markets": markets, "profiles": profiles,
        "market_count_required": len(required),
        "market_count_complete": sum(m["metadata_complete"] for m in markets.values()),
        "cash_equivalence_assumed": False,
        "remaining_execution_requirements": [
            "APPROVE_EXACT_INSTRUMENTS_AND_VENUE_ACCOUNT",
            "DEFINE_CASH_QUOTE_FX_AND_COST_POLICY",
            "ENFORCE_ORDER_FILTERS_WITH_THEIR_REFERENCE_PRICE_WINDOWS",
            "FREEZE_CALENDAR_HOLD_STOP_AND_PRECEDENCE",
            "PROSPECTIVE_ACTIVATION_AND_FRESH_EXECUTION_QUOTES",
        ],
        "research_only": True, "production_activation": False,
        "orders": 0, "real_capital": 0, "economic_observations_created": 0,
    }
    return dict(result, audit_sha256=book.digest(result))
