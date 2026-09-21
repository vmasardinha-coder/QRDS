import json, time, statistics
from datetime import datetime, timezone
import ccxt

EXCHANGES = {
    'okx': ccxt.okx({'enableRateLimit': True}),
    'bybit': ccxt.bybit({'enableRateLimit': True}),
    'bitget': ccxt.bitget({'enableRateLimit': True}),
}
SYMBOL = 'BTC/USDT'
SNAPSHOTS = 20
SLEEP_SECONDS = 2
QUOTE_NOTIONAL = 1000.0
MAKER_FEE = 0.0010
TAKER_FEE = 0.0010
LATENCY_HAIRCUT = 0.0005
TOTAL_FRICTION = MAKER_FEE + TAKER_FEE + LATENCY_HAIRCUT


def vwap_ask(book, quote_notional):
    remain = quote_notional
    base = 0.0
    spent = 0.0
    for price, amount in book['asks']:
        cap = price * amount
        take_q = min(remain, cap)
        if take_q <= 0:
            break
        base += take_q / price
        spent += take_q
        remain -= take_q
        if remain <= 1e-9:
            break
    if remain > 1e-6 or base <= 0:
        return None
    return spent / base


def vwap_bid(book, quote_notional):
    remain = quote_notional
    base_sold = 0.0
    received = 0.0
    for price, amount in book['bids']:
        cap = price * amount
        take_q = min(remain, cap)
        if take_q <= 0:
            break
        qty = take_q / price
        base_sold += qty
        received += qty * price
        remain -= take_q
        if remain <= 1e-9:
            break
    if remain > 1e-6 or base_sold <= 0:
        return None
    return received / base_sold

records = []
errors = []
for idx in range(SNAPSHOTS):
    books = {}
    ts = datetime.now(timezone.utc).isoformat()
    for name, ex in EXCHANGES.items():
        try:
            book = ex.fetch_order_book(SYMBOL, limit=20)
            ask = vwap_ask(book, QUOTE_NOTIONAL)
            bid = vwap_bid(book, QUOTE_NOTIONAL)
            if ask is None or bid is None:
                raise RuntimeError('insufficient_depth')
            books[name] = {'ask_vwap': ask, 'bid_vwap': bid}
        except Exception as exc:
            errors.append({'snapshot': idx, 'exchange': name, 'error': repr(exc)})
    names = sorted(books)
    for buy_ex in names:
        for sell_ex in names:
            if buy_ex == sell_ex:
                continue
            ask = books[buy_ex]['ask_vwap']
            bid = books[sell_ex]['bid_vwap']
            gross = bid / ask - 1.0
            net = gross - TOTAL_FRICTION
            records.append({
                'snapshot': idx,
                'timestamp_utc': ts,
                'buy_exchange': buy_ex,
                'sell_exchange': sell_ex,
                'buy_ask_vwap': ask,
                'sell_bid_vwap': bid,
                'gross_spread': gross,
                'net_after_frozen_friction': net,
            })
    if idx + 1 < SNAPSHOTS:
        time.sleep(SLEEP_SECONDS)

pair_stats = {}
for key in sorted({(r['buy_exchange'], r['sell_exchange']) for r in records}):
    xs = [r for r in records if (r['buy_exchange'], r['sell_exchange']) == key]
    gross = [r['gross_spread'] for r in xs]
    net = [r['net_after_frozen_friction'] for r in xs]
    pair_stats[f'{key[0]}->{key[1]}'] = {
        'n': len(xs),
        'gross_mean_bps': statistics.mean(gross) * 10000 if gross else None,
        'gross_max_bps': max(gross) * 10000 if gross else None,
        'net_mean_bps': statistics.mean(net) * 10000 if net else None,
        'net_max_bps': max(net) * 10000 if net else None,
        'net_positive_count': sum(x > 0 for x in net),
    }

report = {
    'source_system': 'hummingbot',
    'family': 'cross_exchange_market_making',
    'research_only': True,
    'shadow_only': True,
    'factory_modified': False,
    'probe_type': 'contemporaneous_order_book_vwap_probe',
    'symbol': SYMBOL,
    'quote_notional': QUOTE_NOTIONAL,
    'frozen_friction': {
        'maker_fee': MAKER_FEE,
        'taker_fee': TAKER_FEE,
        'latency_haircut': LATENCY_HAIRCUT,
        'total_bps': TOTAL_FRICTION * 10000,
    },
    'snapshots_requested': SNAPSHOTS,
    'sleep_seconds': SLEEP_SECONDS,
    'pair_stats': pair_stats,
    'errors': errors,
    'records': records,
    'limitations': [
        'short contemporaneous sample, not historical replay',
        'generic frozen fees, not account-tier-specific fees',
        'no queue-position model for maker leg',
        'no transfer/capital-fragmentation cost',
    ],
}
print(json.dumps(report, indent=2, sort_keys=True))
