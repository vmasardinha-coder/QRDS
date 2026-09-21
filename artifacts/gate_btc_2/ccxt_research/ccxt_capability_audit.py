import json, ccxt

PINNED_SHA = "6c98f320d87cab3fe2224a65bd293dd15673c31d"
targets = ["okx", "kraken", "coinbase"]
report = {
    "research_only": True,
    "shadow_only": True,
    "factory_modified": False,
    "upstream_sha": PINNED_SHA,
    "exchange_count": len(ccxt.exchanges),
    "targets": {},
    "classification": "COMPONENT_AUDITOR_NOT_ALPHA_SOURCE",
}

for exid in targets:
    cls = getattr(ccxt, exid)
    ex = cls({"enableRateLimit": True})
    d = ex.describe()
    has = d.get("has", {})
    report["targets"][exid] = {
        "fetch_ohlcv": bool(has.get("fetchOHLCV")),
        "fetch_trades": bool(has.get("fetchTrades")),
        "fetch_order_book": bool(has.get("fetchOrderBook")),
        "create_order": bool(has.get("createOrder")),
        "cancel_order": bool(has.get("cancelOrder")),
        "rate_limit_ms": d.get("rateLimit"),
        "timeframes_declared": sorted((d.get("timeframes") or {}).keys())[:20],
    }

assert report["exchange_count"] > 50
assert all(x in ccxt.exchanges for x in targets)
assert all(report["targets"][x]["fetch_ohlcv"] for x in targets)
assert all(report["targets"][x]["fetch_trades"] for x in targets)
assert all(report["targets"][x]["fetch_order_book"] for x in targets)

print(json.dumps(report, indent=2, sort_keys=True))
