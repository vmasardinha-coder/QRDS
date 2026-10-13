"""Exact-source history extension for future PIT150 collections only."""
from __future__ import annotations
import hashlib
import json
import math
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

EFFECTIVE_CUTOFF = "2026-10-13"
ROUTES = {'DRV': {'coin_id': 'derive', 'name': 'Derive', 'source': 'gate', 'pair': 'DRV_USDT'},
 'CARDS': {'coin_id': 'collector-crypt',
           'name': 'Collector Crypt',
           'source': 'mexc',
           'pair': 'CARDSUSDT',
           'contract': 'CARDSccUMFKoPRZxt5vt3ksUbxEFEcnZ3H2pd3dKxYjp'},
 'BP': {'coin_id': 'backpack',
        'name': 'Backpack',
        'source': 'mexc',
        'pair': 'BPUSDT',
        'contract': 'BPxxfRCXkUVhig4HS1Lh7kZqV6SPJhzfEk4x6fVBjPCy'},
 'SHFL': {'coin_id': 'shuffle-2',
          'name': 'Shuffle',
          'source': 'xt',
          'pair': 'shfl_usdt',
          'contract': '0x8881562783028f5c1bcb985d2283d5e170d88888'},
 'MNT': {'coin_id': 'mantle',
         'name': 'Mantle',
         'source': 'mexc',
         'pair': 'MNTUSDT',
         'contract': '0x3c3a81e81dc49A522A592e7622A7E711c06bf354'},
 'HTX': {'coin_id': 'htx-dao',
         'name': 'HTX DAO',
         'source': 'mexc',
         'pair': 'HTXUSDT',
         'contract': 'TUPM7K8REVzD2UdV4R5fe5M8XbnR2DdoJ6'},
 'BGB': {'coin_id': 'bitget-token',
         'name': 'Bitget Token',
         'source': 'mexc',
         'pair': 'BGBUSDT',
         'contract': '0x54D2252757e1672EEaD234D27B1270728fF90581'},
 'KAS': {'coin_id': 'kaspa', 'name': 'Kaspa', 'source': 'mexc', 'pair': 'KASUSDT', 'contract': ''},
 'KCS': {'coin_id': 'kucoin-shares',
         'name': 'KuCoin Token',
         'source': 'mexc',
         'pair': 'KCSUSDT',
         'contract': '0xf34960d9d60be18cc1d5afc1a6f012a723a28811'},
 'BDX': {'coin_id': 'beldex', 'name': 'Beldex', 'source': 'mexc', 'pair': 'BDXUSDT', 'contract': ''},
 'XDC': {'coin_id': 'xdce-crowd-sale',
         'name': 'XDC Network',
         'source': 'mexc',
         'pair': 'XDCUSDT',
         'contract': ''},
 'AKE': {'coin_id': 'akedo',
         'name': 'AKEDO',
         'source': 'mexc',
         'pair': 'AKEUSDT',
         'contract': '0x2c3a8Ee94dDD97244a93Bc48298f97d2C412F7Db'},
 'BSV': {'coin_id': 'bitcoin-cash-sv',
         'name': 'BitcoinSV',
         'source': 'mexc',
         'pair': 'BSVUSDT',
         'contract': ''},
 'APEPE': {'coin_id': 'ape-and-pepe',
           'name': 'APE and PEPE',
           'source': 'mexc',
           'pair': 'APEPEUSDT',
           'contract': '0xA3f751662e282E83EC3cBc387d225Ca56dD63D3A'}}

def route_for_member(symbol, coin_id, cutoff):
    if cutoff and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",cutoff):
        raise ValueError("invalid qualified source cutoff")
    if not cutoff or cutoff < EFFECTIVE_CUTOFF:
        return None
    route = ROUTES.get(symbol)
    if not route or route["coin_id"] != coin_id:
        return None
    datetime.strptime(cutoff, "%Y-%m-%d")
    return dict(route)

def check_identity(route, payload):
    provider = route["source"]
    if provider == "gate":
        if not (payload.get("id") == route["pair"] and payload.get("base") == "DRV"
                and payload.get("quote") == "USDT" and payload.get("base_name") == route["name"]
                and payload.get("trade_status") == "tradable"):
            raise ValueError("exact Gate identity/market mismatch")
    elif provider == "mexc":
        rows = payload.get("symbols", [])
        if len(rows) != 1:
            raise ValueError("ambiguous MEXC identity")
        entry = rows[0]
        if not (entry.get("symbol") == route["pair"] and entry.get("quoteAsset") == "USDT"
                and entry.get("fullName") == route["name"]
                and entry.get("contractAddress") == route["contract"]
                and entry.get("isSpotTradingAllowed") is True):
            raise ValueError("exact MEXC identity/contract mismatch")
    elif provider == "xt":
        rows = payload.get("result", {}).get("symbols", [])
        if payload.get("rc") != 0 or len(rows) != 1:
            raise ValueError("ambiguous XT identity")
        entry = rows[0]
        contracts = {x.get("contract", "").lower() for x in entry.get("chainRelation", [])}
        if not (entry.get("symbol") == route["pair"] and entry.get("baseCurrency") == "shfl"
                and entry.get("quoteCurrency") == "usdt" and entry.get("state") == "ONLINE"
                and route["contract"].lower() in contracts):
            raise ValueError("exact XT token contract mismatch")
    else:
        raise ValueError("unsupported qualified route")

def normalize_history(symbol, route, payload, cutoff):
    provider = route["source"]
    if provider == "xt":
        if payload.get("rc") != 0:
            raise ValueError("XT history transport/schema failure")
        raw_rows = payload.get("result", [])
    else:
        raw_rows = payload
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("empty qualified history")
    rows = []
    for entry in raw_rows:
        if provider == "gate":
            ts = int(entry[0]);o,h,l,c,v = map(float, [entry[5],entry[3],entry[4],entry[2],entry[1]])
        elif provider == "mexc":
            ts = int(entry[0]) // 1000;o,h,l,c,v = map(float, [entry[1],entry[2],entry[3],entry[4],entry[7]])
        else:
            ts = int(entry["t"]) // 1000;o,h,l,c,v = map(float, [entry["o"],entry["h"],entry["l"],entry["c"],entry["v"]])
        date = datetime.fromtimestamp(ts, timezone.utc).date().isoformat()
        if date > cutoff:
            continue
        if ts % 86400 or not all(math.isfinite(x) and x > 0 for x in [o,h,l,c]):
            raise ValueError("invalid UTC/physical OHLC")
        if not (l <= min(o,c) <= max(o,c) <= h) or not math.isfinite(v) or v < 0:
            raise ValueError("invalid OHLC/quote-volume semantics")
        rows.append({"date":date,"symbol":symbol,"close_usd":c,"volume_usd":v,"source":provider})
    rows.sort(key=lambda x:x["date"])
    dates = [x["date"] for x in rows]
    if len(dates) != len(set(dates)):
        raise ValueError("duplicate qualified daily history")
    if len(rows) < 200:
        raise ValueError(f"only {len(rows)} rows")
    expected = [(datetime.strptime(cutoff,"%Y-%m-%d").date()-timedelta(days=i)).isoformat() for i in range(199,-1,-1)]
    if dates[-200:] != expected:
        raise ValueError("qualified history lacks 200 consecutive closes through cutoff")
    return rows

def collect_history(session, symbol, coin_id, cutoff, evidence_dir, now=None):
    route = route_for_member(symbol, coin_id, cutoff)
    if route is None:
        return None
    if cutoff >= (now or datetime.now(timezone.utc)).date().isoformat():
        raise ValueError("qualified source cutoff is not a completed UTC day")
    provider,pair = route["source"],route["pair"]
    if provider == "gate":
        urls = [f"https://api.gateio.ws/api/v4/spot/currency_pairs/{pair}",f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1d&limit=1000"]
    elif provider == "mexc":
        urls = [f"https://api.mexc.com/api/v3/exchangeInfo?symbol={pair}",f"https://api.mexc.com/api/v3/klines?symbol={pair}&interval=1d&limit=1000"]
    else:
        urls = [f"https://sapi.xt.com/v4/public/symbol?symbol={pair}",f"https://sapi.xt.com/v4/public/kline?symbol={pair}&interval=1d&limit=1000"]
    output = Path(evidence_dir)/symbol;output.mkdir(parents=True,exist_ok=True)
    payloads,hashes = [],[]
    for label,url in zip(["identity","candles"],urls):
        response = session.get(url,timeout=30)
        if response.status_code != 200:
            raise ValueError(f"qualified {provider} {label} HTTP {response.status_code}")
        raw = response.content
        (output/f"{label}.json").write_bytes(raw)
        payloads.append(json.loads(raw));hashes.append(hashlib.sha256(raw).hexdigest())
        if label == "identity":
            check_identity(route,payloads[-1])
    rows = normalize_history(symbol,route,payloads[1],cutoff)
    evidence = {"symbol":symbol,"coin_id":coin_id,"source":provider,"source_pair":pair,
                "cutoff":cutoff,"effective_cutoff":EFFECTIVE_CUTOFF,"closed_rows":len(rows),
                "identity_sha256":hashes[0],"candles_sha256":hashes[1],
                "public_execution_ohlcv":True,"historical_scientific_credit":0,
                "research_only":True,"orders":0,"real_capital":0}
    (output/"qualification.json").write_text(json.dumps(evidence,indent=2)+"\n")
    return rows,evidence
