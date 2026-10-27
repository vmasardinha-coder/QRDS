"""Exact-source history extension for future PIT150 collections only."""
from __future__ import annotations
import hashlib
import json
import math
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

EFFECTIVE_CUTOFF = "2026-10-13"
GATE_FOLLOWUP_ROUTES = {
    'CRVUSD': {'coin_id': 'crvusd', 'name': 'crvUSD', 'source': 'gate', 'pair': 'CRVUSD_USDT', 'contract': '0xf939e0a03fb07f59a73314e73794be0e57ac1b4e', 'contract_chain': 'ETH'},
    'GRAM': {'coin_id':'the-open-network','name':'GRAM (prev. Toncoin)','source':'gate','pair':'GRAM_USDT','contract':'','contract_chain':'TON','rename_evidence':'https://www.gate.com/pt-br/announcements/article/100181'},
    'GRASS': {'coin_id':'grass','name':'Grass','source':'gate','pair':'GRASS_USDT','contract':'Grass7B4RdKfBCjTKgSqnXkqjwiGvQyFbuSCUJr3XXjs','contract_chain':'SOL'},
    'GT': {'coin_id':'gatechain-token','name':'GateToken','source':'gate','pair':'GT_USDT'},
    'GHO': {'coin_id':'gho','name':'GHO','source':'gate','pair':'GHO_USDT'},
    'PIEVERSE': {'coin_id':'pieverse','name':'Pieverse','source':'gate','pair':'PIEVERSE_USDT'},
    'AERO': {'coin_id':'aerodrome-finance','name':'Aerodrome','source':'gate','pair':'AERO_USDT','contract':'0x940181a94A35A4569E4529A3CDfB74e38FD98631','contract_chain':'BASEEVM'},
    'SPX': {'coin_id':'spx6900','name':'SPX6900','source':'gate','pair':'SPX_USDT','contract':'0xe0f63a424a4439cbe457d80e4f4b51ad25b2c56c','contract_chain':'ETH'},
}
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
ROUTES.update(GATE_FOLLOWUP_ROUTES)
ROUTES['BTW'] = {'coin_id':'bitway','name':'Bitway','source':'bitget','pair':'BTWUSDT','contract':'0x444045b0ee1ee319a660a5e3d604ca0ffa35acaa','contract_chain':'BEP20'}
ROUTES['USYC'] = {'coin_id':'hashnote-usyc','name':'Circle USYC','source':'deribit','pair':'USYC_USDC','instrument_id':377252,'base_currency_uuid':'4c559e06-44d0-411c-bb36-1a4812df4510','quote_currency':'USDC','identity_evidence':'https://insights.deribit.com/exchange-updates/deribit-introduces-hashnotes-usyc-as-new-yield-bearing-cross-margin-collateral-option/'}

# Public spot execution history; first usable cutoff follows this qualification.
ROUTES['USDY'] = {'coin_id':'ondo-us-dollar-yield','name':'Ondo U.S. Dollar Yield',
                 'source':'bybit','pair':'USDYUSDT','symbol_id':555,
                 'effective_cutoff':'2026-10-15',
                 'identity_evidence':'https://www.bybit.com/en/learn/stablecoin/what-is-ondo-us-dollar-yield-usdy'}

ROUTES['USDGO'] = {'coin_id':'usdgo','name':'USDGO','source':'bitget',
                   'pair':'USDGOUSDT','base_coin':'USDGO',
                   'contract':'72puLt71H93Z9CzHuBRTwFpL4TG3WZUhnoCC7p8gxigu',
                   'contract_chain':'SOL','currency_id':'2091',
                   'effective_cutoff':'2026-10-15',
                   'identity_evidence':'https://www.bitget.com/support/articles/12560603859340'}

# Exact Alpha token identity and independent exchange pair metadata are both required.
ROUTES['KOGE'] = {'coin_id':'bnb48-club-token','name':'48 Club Token',
                  'source':'binance_alpha','pair':'ALPHA_22USDT','alpha_id':'ALPHA_22',
                  'chain_id':'56','contract':'0xe6df05ce8c8301223373cf5b969afcb1498c5528',
                  'effective_cutoff':'2026-10-16',
                  'identity_evidence':'https://web3.48.club/docs/koge-token'}


# Exact Ethereum pool, with canonical closing blocks/logs independently checked.
ROUTES['A7A5'] = {'coin_id':'a7a5','name':'A7A5',
    'source':'blockscout_eth_a7a5_swaps','pair':'A7A5_USDT_ETH_POOL',
    'pool':'0x14d7aab5b4bca6a02e52ac22520b033bf35f4091',
    'effective_cutoff':'2026-10-17'}


# Same frozen REUSD/USDT pool, reconstructed from physical Fluid executions.
ROUTES['REUSD'] = {'coin_id':'re-protocol-reusd','name':'Re Protocol Deposit Token',
    'source':'blockscout_eth_reusd_swaps','pair':'REUSD_USDT_ETH_POOL',
    'pool':'0xb96cee75211700bc148b95b1c907d726791f4457',
    'effective_cutoff':'2026-10-17'}

# Physical Figure trade clock and TRADE close; all tape cashflow must reconcile
# with canonical native settlement proofs. Aggregated message VWAP is not close.
ROUTES['HASH'] = {'coin_id':'hash-2','name':'Provenance Blockchain',
    'source':'figure_hash_native_reconciled_tape','pair':'HASH-USD',
    'effective_cutoff':'2026-10-17'}

# Native Akash chain, bound independently to Gate currency and spot metadata.
ROUTES['AKT'] = {'coin_id':'akash-network','name':'Akash Network',
    'source':'gate','pair':'AKT_USDT','contract':'','contract_chain':'AKT',
    'native_asset':True,'effective_cutoff':'2026-10-17',
    'identity_evidence':'https://www.gate.com/fr/announcements/article/19761/Gate.io-will-list-Akash-Network-AKT',
    'issuer_identity_evidence':'https://akash.network/token/'}


# Exact Solana pool already bound in the source registry; only future cutoffs
# may use the newly verified 200-day paginated history.
ROUTES['USX'] = {'coin_id': 'usx', 'name': 'USX Stablecoin',
                 'source': 'geckoterminal_exact_usx_pool', 'pair': 'USX-USDC',
                 'effective_cutoff': '2026-10-27'}

def route_for_member(symbol, coin_id, cutoff):
    if cutoff and not re.fullmatch(r"\d{4}-\d{2}-\d{2}",cutoff):
        raise ValueError("invalid qualified source cutoff")
    if not cutoff or cutoff < EFFECTIVE_CUTOFF:
        return None
    route = ROUTES.get(symbol)
    if not route or route["coin_id"] != coin_id or cutoff < route.get("effective_cutoff", EFFECTIVE_CUTOFF):
        return None
    datetime.strptime(cutoff, "%Y-%m-%d")
    selected = dict(route)
    if symbol == 'AERO' and cutoff >= '2026-10-27':
        # Gate changed only its provider display name. The exact Base contract,
        # CoinGecko identity, pair, chain and tradability checks stay mandatory.
        # Never reinterpret cutoffs before this reviewed amendment.
        selected['name'] = 'Aero'
        selected['provider_name_amendment'] = {
            'effective_cutoff': '2026-10-27',
            'previous_name': 'Aerodrome', 'provider_name': 'Aero',
            'evidence': 'artifacts/gate_btc_2/pit150_aero_gate_name_20261027/IDENTITY_RECEIPT.json',
            'contract_and_chain_unchanged': True,
        }
    return selected

def check_identity(route, payload):
    provider = route["source"]
    if provider == "gate":
        if not (payload.get("id") == route["pair"] and payload.get("base") == route["pair"].split('_')[0]
                and payload.get("quote") == "USDT" and payload.get("base_name") == route["name"]
                and payload.get("trade_status") == "tradable"):
            raise ValueError("exact Gate identity/market mismatch")
    elif provider == "bybit":
        result = payload.get("result", {})
        rows = result.get("list", [])
        if payload.get("retCode") != 0 or result.get("category") != "spot" or len(rows) != 1:
            raise ValueError("ambiguous Bybit spot identity")
        entry = rows[0]
        if not (entry.get("symbol") == route["pair"] and entry.get("symbolId") == route["symbol_id"]
                and entry.get("baseCoin") == "USDY" and entry.get("quoteCoin") == "USDT"
                and entry.get("status") == "Trading"):
            raise ValueError("exact Bybit USDY spot identity mismatch")

    elif provider == 'binance_alpha':
        rows = payload.get('data', [])
        if payload.get('code') != '000000' or payload.get('success') is not True or not isinstance(rows,list):
            raise ValueError('invalid Binance Alpha token response')
        matches = [x for x in rows if x.get('alphaId') == route['alpha_id'] or x.get('symbol') == 'KOGE']
        if len(matches) != 1:
            raise ValueError('ambiguous Binance Alpha exact token identity')
        entry = matches[0]
        if not (entry.get('alphaId') == route['alpha_id'] and entry.get('symbol') == 'KOGE'
                and entry.get('name') == route['name'] and entry.get('chainId') == route['chain_id']
                and str(entry.get('contractAddress','')).lower() == route['contract'].lower()
                and entry.get('offline') is False and entry.get('fullyDelisted') is False):
            raise ValueError('exact Binance Alpha token/chain/contract mismatch')
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
    elif provider == 'deribit':
        entry = payload.get('result', {})
        if not (payload.get('jsonrpc') == '2.0' and payload.get('testnet') is False
                and not payload.get('error') and entry.get('instrument_name') == route['pair']
                and entry.get('instrument_id') == route['instrument_id']
                and entry.get('base_currency_uuid') == route['base_currency_uuid']
                and entry.get('kind') == 'spot' and entry.get('state') == 'open'
                and entry.get('is_active') is True and entry.get('base_currency') == 'USYC'
                and entry.get('quote_currency') == entry.get('counter_currency') == 'USDC'):
            raise ValueError('exact Deribit spot instrument identity mismatch')
    elif provider == "bitget":
        rows = payload.get('data', [])
        if payload.get('code') != '00000' or len(rows) != 1:
            raise ValueError('ambiguous Bitget spot identity')
        entry = rows[0]
        if not (entry.get('symbol') == route['pair'] and entry.get('baseCoin') == route.get('base_coin', 'BTW')
                and entry.get('quoteCoin') == 'USDT' and entry.get('status') == 'online'):
            raise ValueError('exact Bitget spot identity mismatch')
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

def check_alpha_exchange(route, payload):
    data = payload.get('data', {})
    if payload.get('code') != '000000' or payload.get('success') is not True or data.get('timezone') != 'UTC':
        raise ValueError('invalid Binance Alpha exchange response/timezone')
    entries = [x for x in data.get('symbols', []) if x.get('symbol') == route['pair']]
    if len(entries) != 1 or not (entries[0].get('baseAsset') == route['alpha_id']
            and entries[0].get('quoteAsset') == 'USDT' and entries[0].get('status') == 'TRADING'):
        raise ValueError('exact Binance Alpha pair identity mismatch')


def check_gate_contract(route, payload):
    expected_base = route['pair'].split('_')[0]
    def same_contract(value):
        actual = str(value)
        expected = route['contract']
        return actual.lower() == expected.lower() if expected.startswith('0x') else actual == expected
    matches = [entry for entry in payload.get('chains', [])
               if entry.get('name') == route['contract_chain']
               and same_contract(entry.get('addr'))]
    if not (payload.get('currency') == expected_base and payload.get('name') == route['name']
            and payload.get('delisted') is False and payload.get('trade_disabled') is False
            and len(matches) == 1):
        raise ValueError('exact Gate chain/token contract mismatch')
    if route.get('native_asset') and payload.get('chain') != route['contract_chain']:
        raise ValueError('exact Gate native primary chain mismatch')

def check_bitget_contract(route, payload):
    rows = payload.get('data', [])
    if payload.get('code') != '00000' or len(rows) != 1 or rows[0].get('coin') != route.get('base_coin', 'BTW'):
        raise ValueError('ambiguous Bitget currency identity')
    if route.get('currency_id') and rows[0].get('coinId') != route['currency_id']:
        raise ValueError('exact Bitget currency identifier mismatch')
    expected = route['contract']
    def same_contract(value):
        actual = str(value)
        return actual.lower() == expected.lower() if expected.startswith('0x') else actual == expected
    matches = [x for x in rows[0].get('chains', []) if x.get('chain') == route['contract_chain']
               and same_contract(x.get('contractAddress', ''))]
    if len(matches) != 1:
        raise ValueError('exact Bitget chain/token contract mismatch')

def deribit_utc_daily_rows(payload, cutoff):
    result = payload.get('result', {})
    fields = ['ticks','open','high','low','close','volume','cost']
    if (payload.get('jsonrpc') != '2.0' or payload.get('testnet') is not False
            or payload.get('error') or result.get('status') != 'ok'
            or any(not isinstance(result.get(k), list) for k in fields)):
        raise ValueError('invalid Deribit hourly response')
    if any(len(result[k]) != len(result['ticks']) for k in fields):
        raise ValueError('inconsistent Deribit hourly arrays')
    end = datetime.strptime(cutoff,'%Y-%m-%d').replace(tzinfo=timezone.utc)+timedelta(days=1)
    start_ms = int((end-timedelta(days=200)).timestamp()*1000)
    end_ms = int(end.timestamp()*1000)
    hours = []
    for i,tick in enumerate(result['ticks']):
        if not isinstance(tick, int) or tick % 3600000:
            raise ValueError('unaligned Deribit UTC hour')
        if not start_ms <= tick < end_ms:
            continue
        o,h,l,c,v,cost = [float(result[k][i]) for k in fields[1:]]
        if (not all(math.isfinite(x) and x>0 for x in [o,h,l,c])
                or not l<=min(o,c)<=max(o,c)<=h
                or not all(math.isfinite(x) and x>=0 for x in [v,cost])):
            raise ValueError('invalid Deribit hourly OHLC/quote cost')
        hours.append((tick,o,h,l,c,cost))
    hours.sort()
    if [x[0] for x in hours] != list(range(start_ms,end_ms,3600000)):
        raise ValueError('Deribit history lacks 4800 unique consecutive UTC hours')
    daily=[]
    for i in range(0,4800,24):
        day=hours[i:i+24]
        daily.append([day[0][0]//1000,sum(x[5] for x in day),day[-1][4],
                      max(x[2] for x in day),min(x[3] for x in day),day[0][1]])
    return daily

def normalize_history(symbol, route, payload, cutoff):
    provider = route["source"]
    if provider == "bybit":
        result = payload.get("result", {})
        if (payload.get("retCode") != 0 or result.get("category") != "spot"
                or result.get("symbol") != route["pair"]):
            raise ValueError("Bybit history transport/spot identity failure")
        raw_rows = result.get("list", [])
    elif provider == 'deribit':
        raw_rows = deribit_utc_daily_rows(payload,cutoff)

    elif provider == 'binance_alpha':
        if payload.get('code') != '000000' or payload.get('success') is not True:
            raise ValueError('Binance Alpha history transport failure')
        raw_rows = payload.get('data', [])
    elif provider == 'bitget':
        if payload.get('code') != '00000':
            raise ValueError('Bitget history transport/schema failure')
        raw_rows = payload.get('data', [])
    elif provider == "xt":
        if payload.get("rc") != 0:
            raise ValueError("XT history transport/schema failure")
        raw_rows = payload.get("result", [])
    else:
        raw_rows = payload
    if not isinstance(raw_rows, list) or not raw_rows:
        raise ValueError("empty qualified history")
    rows = []
    for entry in raw_rows:
        if provider in {"gate","deribit"}:
            ts = int(entry[0]);o,h,l,c,v = map(float, [entry[5],entry[3],entry[4],entry[2],entry[1]])
        elif provider == "bybit":
            if len(entry) != 7 or int(entry[0]) % 86400000:
                raise ValueError("invalid Bybit UTC daily schema")
            ts = int(entry[0]) // 1000
            o,h,l,c,v = map(float,[entry[1],entry[2],entry[3],entry[4],entry[6]])
        elif provider == 'bitget':
            if len(entry) not in {7,8} or int(entry[0]) % 86400000:
                raise ValueError('invalid Bitget UTC daily schema')
            ts = int(entry[0]) // 1000;o,h,l,c,v = map(float,[entry[1],entry[2],entry[3],entry[4],entry[6]])

        elif provider == 'binance_alpha':
            if (not isinstance(entry,list) or len(entry) != 12 or int(entry[0]) % 86400000
                    or int(entry[6]) != int(entry[0])+86400000-1
                    or str(entry[11]) != '0'):
                raise ValueError('invalid Binance Alpha completed UTC daily schema')
            ts = int(entry[0]) // 1000
            o,h,l,c,v = map(float,[entry[1],entry[2],entry[3],entry[4],entry[7]])
            base = float(entry[5])
            count = int(entry[8])
            if (not math.isfinite(base) or base < 0 or count < 0 or str(count) != str(entry[8])
                    or (count == 0 and (base != 0 or v != 0))
                    or (count > 0 and (base <= 0 or v <= 0))):
                raise ValueError('invalid Binance Alpha reported volume/trade count')
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

BYBIT_PUBLIC_HOSTS = ("https://api.bybit.com", "https://api.bytick.com")



# A native public-data capture is collected outside the runner's blocked region.
# The branch contains public exchange payloads only; no account or order access.
BYBIT_CAPTURE_BRANCH = "pit150-usdy-public-captures"
BYBIT_CAPTURE_EFFECTIVE_CUTOFF = "2026-10-16"
BYBIT_CAPTURE_REPOSITORY = "vmasardinha-coder/QRDS"


def load_bybit_public_capture(session, route, symbol, cutoff, evidence_dir, now=None):
    observed = now or datetime.now(timezone.utc)
    boundary = datetime.strptime(cutoff, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    if boundary > observed:
        raise ValueError("public capture cutoff is unfinished")
    api = f"https://api.github.com/repos/{BYBIT_CAPTURE_REPOSITORY}"
    # Use the runner's read-only repository token only on GitHub's API.
    # Public exchange and raw payload requests never receive this credential.
    import os
    token = os.environ.get("GATE_BTC_PUBLIC_CAPTURE_READ_TOKEN", "").strip()
    kwargs = {"timeout": 30}
    if token:
        kwargs["headers"] = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    response = session.get(f"{api}/commits?sha={BYBIT_CAPTURE_BRANCH}&per_page=1", **kwargs)
    if response.status_code != 200:
        raise ValueError(f"public capture commit HTTP {response.status_code}")
    head = json.loads(response.content)[0]
    revision = head["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("invalid public capture revision")
    published = datetime.fromisoformat(head["commit"]["committer"]["date"].replace("Z", "+00:00"))
    if published.tzinfo is None or not boundary <= published <= observed:
        raise ValueError("public capture publication time is not causal")
    prefix = f"https://raw.githubusercontent.com/{BYBIT_CAPTURE_REPOSITORY}/{revision}/captures/{cutoff}"
    payloads = {}
    for label in ("seal", "identity", "candles"):
        r = session.get(f"{prefix}/{label}.json", timeout=30)
        if r.status_code != 200:
            raise ValueError(f"public capture {label} HTTP {r.status_code}")
        payloads[label] = r.content
    seal = json.loads(payloads["seal"])
    if not (seal.get("schema") == "gate_btc.bybit_public_capture.v1"
            and seal.get("symbol") == symbol and seal.get("coin_id") == route["coin_id"]
            and seal.get("pair") == route["pair"] and seal.get("cutoff") == cutoff
            and seal.get("public_api_host") in BYBIT_PUBLIC_HOSTS
            and seal.get("orders") == 0 and seal.get("real_capital") == 0):
        raise ValueError("public capture identity or contract mismatch")
    fetched = datetime.fromisoformat(seal["fetched_at_utc"].replace("Z", "+00:00"))
    if fetched.tzinfo is None or not boundary <= fetched <= published:
        raise ValueError("public capture fetch time is not causal")
    hashes = {k: hashlib.sha256(payloads[k]).hexdigest() for k in ("identity", "candles")}
    if any(seal.get("sha256", {}).get(k + ".json") != v for k, v in hashes.items()):
        raise ValueError("public capture payload hash mismatch")
    check_identity(route, json.loads(payloads["identity"]))
    rows = normalize_history(symbol, route, json.loads(payloads["candles"]), cutoff)
    evidence = {
        "symbol": symbol, "coin_id": route["coin_id"], "source": "bybit",
        "source_pair": route["pair"], "cutoff": cutoff, "closed_rows": len(rows),
        "effective_cutoff": BYBIT_CAPTURE_EFFECTIVE_CUTOFF,
        "public_api_host": seal["public_api_host"],
        "identity_sha256": hashes["identity"], "candles_sha256": hashes["candles"],
        "delivery": "PUBLIC_EXCHANGE_CAPTURE_PINNED_GITHUB_COMMIT",
        "capture_revision": revision, "capture_published_at_utc": published.isoformat(),
        "capture_fetched_at_utc": fetched.isoformat(),
        "seal_sha256": hashlib.sha256(payloads["seal"]).hexdigest(),
        "symbol_id": route["symbol_id"], "quote_currency": "USDT",
        "volume_field": "turnover", "quote_usd_convention": "nominal stablecoin quote; no historical FX conversion",
        "public_execution_ohlcv": True, "historical_scientific_credit": 0,
        "research_only": True, "orders": 0, "real_capital": 0,
        "identity_evidence": route["identity_evidence"], "cross_host_payload_mixing": False,
    }
    output = Path(evidence_dir) / symbol
    output.mkdir(parents=True, exist_ok=True)
    for label, raw in payloads.items():
        (output / f"{label}.json").write_bytes(raw)
    (output / "qualification.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    return rows, evidence


def _collect_bybit(session, symbol, coin_id, route, cutoff, evidence_dir, now=None):
    """Official same-venue hosts; retry availability failures, never identity QA."""
    output = Path(evidence_dir) / symbol
    output.mkdir(parents=True, exist_ok=True)
    end_ms = int((datetime.strptime(cutoff, '%Y-%m-%d').replace(tzinfo=timezone.utc)
                  + timedelta(days=1)).timestamp() * 1000) - 1
    pair = route['pair']
    paths = [f'/v5/market/instruments-info?category=spot&symbol={pair}',
             f'/v5/market/kline?category=spot&symbol={pair}&interval=D&limit=1000&end={end_ms}']
    attempts = []
    for host in BYBIT_PUBLIC_HOSTS:
        raw_payloads = []
        for label, path in zip(('identity', 'candles'), paths):
            response = session.get(host + path, timeout=30)
            attempt = {'host': host, 'label': label, 'http_status': response.status_code}
            attempts.append(attempt)
            (output / 'host_attempts.json').write_text(json.dumps(attempts, indent=2) + '\n')
            if response.status_code != 200:
                if response.status_code in (403, 429) or response.status_code >= 500:
                    break
                raise ValueError(f'qualified bybit {label} HTTP {response.status_code}')
            raw = response.content
            payload = json.loads(raw)
            if label == 'identity':
                check_identity(route, payload)
            else:
                rows = normalize_history(symbol, route, payload, cutoff)
            raw_payloads.append(raw)
        if len(raw_payloads) != 2:
            continue
        for label, raw in zip(('identity', 'candles'), raw_payloads):
            (output / f'{label}.json').write_bytes(raw)
        evidence = {
            'symbol': symbol, 'coin_id': coin_id, 'source': 'bybit', 'source_pair': pair,
            'cutoff': cutoff, 'effective_cutoff': route['effective_cutoff'],
            'closed_rows': len(rows), 'identity_sha256': hashlib.sha256(raw_payloads[0]).hexdigest(),
            'candles_sha256': hashlib.sha256(raw_payloads[1]).hexdigest(),
            'public_execution_ohlcv': True, 'historical_scientific_credit': 0,
            'research_only': True, 'orders': 0, 'real_capital': 0,
            'identity_evidence': route['identity_evidence'], 'symbol_id': route['symbol_id'],
            'quote_currency': 'USDT', 'volume_field': 'turnover',
            'quote_usd_convention': 'nominal stablecoin quote; no historical FX conversion',
            'public_api_host': host, 'host_attempts': attempts,
            'host_policy_reference': 'https://bybit-exchange.github.io/docs/v5/guide',
            'cross_host_payload_mixing': False,
        }
        (output / 'qualification.json').write_text(json.dumps(evidence, indent=2) + '\n')
        return rows, evidence
    if cutoff >= BYBIT_CAPTURE_EFFECTIVE_CUTOFF:
        return load_bybit_public_capture(session, route, symbol, cutoff, evidence_dir, now=now)
    failures = '; '.join(f"{x['host']} {x['label']} HTTP {x['http_status']}" for x in attempts)
    raise ValueError('qualified bybit public hosts unavailable: ' + failures)


def collect_history(session, symbol, coin_id, cutoff, evidence_dir, now=None):
    route = route_for_member(symbol, coin_id, cutoff)
    if route is None:
        return None
    if cutoff >= (now or datetime.now(timezone.utc)).date().isoformat():
        raise ValueError("qualified source cutoff is not a completed UTC day")
    provider,pair = route["source"],route["pair"]
    if provider == 'figure_hash_native_reconciled_tape':
        from tools.gate_btc_hash_settlement_history import collect
        return collect(session,cutoff,evidence_dir,now=now)
    if provider == 'geckoterminal_exact_usx_pool':
        from tools.gate_btc_usx_pool_history import collect
        return collect(session,cutoff,evidence_dir,now=now)
    if provider == 'blockscout_eth_reusd_swaps':
        from tools.gate_btc_reusd_swap_history import collect
        return collect(session,cutoff,evidence_dir,now=now)
    if provider == 'blockscout_eth_a7a5_swaps':
        from tools.gate_btc_a7a5_swap_history import collect
        return collect(session,cutoff,evidence_dir,now=now)

    if provider == 'bybit':
        return _collect_bybit(session, symbol, coin_id, route, cutoff, evidence_dir, now=now)
    if provider == "gate":
        urls = [f"https://api.gateio.ws/api/v4/spot/currency_pairs/{pair}",f"https://api.gateio.ws/api/v4/spot/candlesticks?currency_pair={pair}&interval=1d&limit=1000"]
        if route.get('contract_chain'):
            urls.insert(1, f"https://api.gateio.ws/api/v4/spot/currencies/{symbol}")
    elif provider == 'deribit':
        end = datetime.strptime(cutoff,'%Y-%m-%d').replace(tzinfo=timezone.utc)+timedelta(days=1)
        start_ms = int((end-timedelta(days=200)).timestamp()*1000)
        end_ms = int(end.timestamp()*1000)-1
        urls = [f'https://www.deribit.com/api/v2/public/get_instrument?instrument_name={pair}',
                f'https://www.deribit.com/api/v2/public/get_tradingview_chart_data?instrument_name={pair}&start_timestamp={start_ms}&end_timestamp={end_ms}&resolution=60']
    elif provider == 'bitget':
        end_ms = int((datetime.strptime(cutoff,'%Y-%m-%d').replace(tzinfo=timezone.utc)+timedelta(days=1)).timestamp()*1000)
        urls = [f'https://api.bitget.com/api/v2/spot/public/symbols?symbol={pair}',
                f'https://api.bitget.com/api/v2/spot/public/coins?coin={symbol}',
                f'https://api.bitget.com/api/v2/spot/market/history-candles?symbol={pair}&granularity=1Dutc&limit=200&endTime={end_ms}']

    elif provider == 'binance_alpha':
        end_ms = int((datetime.strptime(cutoff,'%Y-%m-%d').replace(tzinfo=timezone.utc)+timedelta(days=1)).timestamp()*1000)-1
        urls = ['https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list',
                'https://www.binance.com/bapi/defi/v1/public/alpha-trade/get-exchange-info',
                f'https://www.binance.com/bapi/defi/v1/public/alpha-trade/klines?symbol={pair}&interval=1d&limit=1000&endTime={end_ms}']
    elif provider == "mexc":
        urls = [f"https://api.mexc.com/api/v3/exchangeInfo?symbol={pair}",f"https://api.mexc.com/api/v3/klines?symbol={pair}&interval=1d&limit=1000"]
    else:
        urls = [f"https://sapi.xt.com/v4/public/symbol?symbol={pair}",f"https://sapi.xt.com/v4/public/kline?symbol={pair}&interval=1d&limit=1000"]
    output = Path(evidence_dir)/symbol;output.mkdir(parents=True,exist_ok=True)
    payloads,hashes = [],[]
    labels = ['identity','currency','candles'] if (provider == 'gate' and route.get('contract_chain')) or provider == 'bitget' else ['identity','candles']

    if provider == 'binance_alpha':
        labels = ['identity','exchange','candles']
    for label,url in zip(labels,urls):
        response = session.get(url,timeout=30)
        if response.status_code != 200:
            raise ValueError(f"qualified {provider} {label} HTTP {response.status_code}")
        raw = response.content
        (output/f"{label}.json").write_bytes(raw)
        payloads.append(json.loads(raw));hashes.append(hashlib.sha256(raw).hexdigest())
        if label == "identity":
            check_identity(route,payloads[-1])
        elif label == 'exchange':
            check_alpha_exchange(route,payloads[-1])
        elif label == 'currency':
            (check_bitget_contract if provider == 'bitget' else check_gate_contract)(route,payloads[-1])
    rows = normalize_history(symbol,route,payloads[-1],cutoff)
    evidence = {"symbol":symbol,"coin_id":coin_id,"source":provider,"source_pair":pair,
                "cutoff":cutoff,"effective_cutoff":route.get("effective_cutoff",EFFECTIVE_CUTOFF),"closed_rows":len(rows),
                "identity_sha256":hashes[0],"candles_sha256":hashes[-1],
                "public_execution_ohlcv":True,"historical_scientific_credit":0,
                "research_only":True,"orders":0,"real_capital":0}
    if provider == 'deribit':
        evidence.update({'aggregation':'24 complete UTC hours per day; open first, high max, low min, close last, cost sum',
                         'quote_currency':'USDC','quote_usd_convention':'nominal stablecoin quote; no historical FX conversion',
                         'hourly_rows':4800,'identity_evidence':route['identity_evidence']})
    if provider == 'bitget':
        evidence.update({'quote_currency':'USDT','volume_field':'quote_volume_index_6',
                         'quote_usd_convention':'nominal stablecoin quote; no historical FX conversion'})
        if route.get('identity_evidence'):
            evidence['identity_evidence'] = route['identity_evidence']

    if provider == 'binance_alpha':
        raw_selected = [x for x in payloads[-1]['data']
                        if datetime.fromtimestamp(int(x[0])/1000,timezone.utc).date().isoformat() <= cutoff]
        raw_selected.sort(key=lambda x:int(x[0]))
        evidence.update({'exchange_identity_sha256':hashes[1],
                         'identity_evidence':route['identity_evidence'],
                         'chain_id':route['chain_id'],'token_contract':route['contract'],
                         'quote_currency':'USDT','volume_field':'quote_volume_index_7',
                         'provider_reported_zero_volume_days_in_last200':[
                             datetime.fromtimestamp(int(x[0])/1000,timezone.utc).date().isoformat()
                             for x in raw_selected[-200:] if float(x[7]) == 0],
                         'collector_forward_fill':False,
                         'quote_usd_convention':'nominal stablecoin quote; no historical FX conversion'})
    if route.get('native_asset'):
        evidence.update({'native_asset':True,'native_chain':route['contract_chain'],
                         'token_contract':route['contract'],'identity_evidence':route['identity_evidence'],
                         'issuer_identity_evidence':route['issuer_identity_evidence'],
                         'quote_currency':'USDT','volume_field':'quote_turnover_index_1',
                         'quote_usd_convention':'nominal stablecoin quote; no historical FX conversion'})
    if route.get('rename_evidence'):
        evidence['rename_evidence'] = route['rename_evidence']
    if route.get('provider_name_amendment'):
        evidence['provider_name_amendment'] = route['provider_name_amendment']
    if 'currency' in labels:
        evidence['currency_identity_sha256'] = hashes[1]
    (output/"qualification.json").write_text(json.dumps(evidence,indent=2)+"\n")
    return rows,evidence

