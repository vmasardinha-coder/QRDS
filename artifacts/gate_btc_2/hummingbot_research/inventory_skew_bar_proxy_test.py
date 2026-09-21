import json, math, time
from datetime import datetime, timezone
import ccxt

SYMBOLS = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT']
TIMEFRAME = '5m'
TARGET_BARS = 8000
START_EQUITY = 10_000.0
TARGET_BASE_RATIO = 0.50
ORDER_VALUE_FRAC = 0.01
SPREAD_PER_SIDE = 0.0020
FEE_PER_FILL = 0.0010
INVENTORY_RANGE_MULTIPLIER = 1.0


def fetch(ex, symbol, total=TARGET_BARS):
    out = []
    ms_per_bar = 5 * 60 * 1000
    since = ex.milliseconds() - total * ms_per_bar
    while len(out) < total:
        limit = min(300, total - len(out))
        batch = ex.fetch_ohlcv(symbol, TIMEFRAME, since=since, limit=limit)
        if not batch:
            break
        if out and batch[0][0] <= out[-1][0]:
            batch = [x for x in batch if x[0] > out[-1][0]]
        if not batch:
            break
        out.extend(batch)
        since = out[-1][0] + 1
        if len(batch) < 50:
            break
        time.sleep(ex.rateLimit / 1000)
    return out[-total:]


def skew_ratios(base_amount, quote_amount, price, target_ratio, base_range):
    total = base_amount * price + quote_amount
    if total <= 0 or base_range <= 0:
        return 0.0, 0.0
    base_value = base_amount * price
    range_value = min(base_range * price, total * 0.5)
    target_value = total * target_ratio
    left = max(target_value - range_value, 0.0)
    right = target_value + range_value

    if base_value < target_value:
        if target_value <= left:
            inv = 0.5
        else:
            inv = max(0.0, min(0.5, 0.5 * (base_value - left) / (target_value - left)))
        bid_adj = 2.0 - 2.0 * inv
    else:
        if right <= target_value:
            inv = 1.0
        else:
            inv = max(0.5, min(1.0, 0.5 + 0.5 * (base_value - target_value) / (right - target_value)))
        bid_adj = 2.0 * (1.0 - inv)
    ask_adj = 2.0 - bid_adj
    return bid_adj, ask_adj


def run(rows, use_skew):
    if len(rows) < 3:
        return {'n_bars': len(rows), 'error': 'insufficient_data'}
    p0 = rows[0][4]
    base = (START_EQUITY * TARGET_BASE_RATIO) / p0
    quote = START_EQUITY * (1.0 - TARGET_BASE_RATIO)
    order_value = START_EQUITY * ORDER_VALUE_FRAC
    equity_curve = []
    inv_dev = []
    fills = 0
    ambiguous_skips = 0
    turnover = 0.0
    fees = 0.0

    for i in range(1, len(rows)):
        ref = rows[i - 1][4]
        high = rows[i][2]
        low = rows[i][3]
        close = rows[i][4]
        bid = ref * (1.0 - SPREAD_PER_SIDE)
        ask = ref * (1.0 + SPREAD_PER_SIDE)
        base_order = order_value / ref

        if use_skew:
            total_order_size = 2.0 * base_order
            base_range = total_order_size * INVENTORY_RANGE_MULTIPLIER
            bid_adj, ask_adj = skew_ratios(base, quote, ref, TARGET_BASE_RATIO, base_range)
        else:
            bid_adj, ask_adj = 1.0, 1.0

        hit_bid = low <= bid
        hit_ask = high >= ask
        if hit_bid and hit_ask:
            ambiguous_skips += 1
        elif hit_bid:
            qty = min(base_order * bid_adj, quote / (bid * (1.0 + FEE_PER_FILL)))
            if qty > 0:
                notional = qty * bid
                fee = notional * FEE_PER_FILL
                base += qty
                quote -= notional + fee
                fills += 1
                turnover += notional
                fees += fee
        elif hit_ask:
            qty = min(base_order * ask_adj, base)
            if qty > 0:
                notional = qty * ask
                fee = notional * FEE_PER_FILL
                base -= qty
                quote += notional - fee
                fills += 1
                turnover += notional
                fees += fee

        equity = base * close + quote
        equity_curve.append(equity)
        ratio = (base * close / equity) if equity > 0 else 0.0
        inv_dev.append(ratio - TARGET_BASE_RATIO)

    peak = -1e99
    mdd = 0.0
    for e in equity_curve:
        peak = max(peak, e)
        if peak > 0:
            mdd = min(mdd, e / peak - 1.0)
    final_close = rows[-1][4]
    final_equity = base * final_close + quote
    final_ratio = (base * final_close / final_equity) if final_equity > 0 else 0.0
    rms_dev = math.sqrt(sum(x*x for x in inv_dev) / len(inv_dev)) if inv_dev else None
    max_abs_dev = max(abs(x) for x in inv_dev) if inv_dev else None
    return {
        'return': final_equity / START_EQUITY - 1.0,
        'max_drawdown': mdd,
        'fills': fills,
        'ambiguous_skips': ambiguous_skips,
        'turnover_quote': turnover,
        'fees_quote': fees,
        'inventory_rms_deviation': rms_dev,
        'inventory_max_abs_deviation': max_abs_dev,
        'final_base_ratio': final_ratio,
        'final_equity': final_equity,
    }


ex = ccxt.okx({'enableRateLimit': True})
results = {}
for symbol in SYMBOLS:
    rows = fetch(ex, symbol)
    static = run(rows, False)
    skewed = run(rows, True)
    delta = {
        'return_pp': (skewed.get('return', 0) - static.get('return', 0)) * 100,
        'max_drawdown_pp': (skewed.get('max_drawdown', 0) - static.get('max_drawdown', 0)) * 100,
        'inventory_rms_delta_pp': (skewed.get('inventory_rms_deviation', 0) - static.get('inventory_rms_deviation', 0)) * 100,
        'inventory_max_abs_delta_pp': (skewed.get('inventory_max_abs_deviation', 0) - static.get('inventory_max_abs_deviation', 0)) * 100,
    }
    results[symbol] = {
        'bars': len(rows),
        'start': datetime.fromtimestamp(rows[0][0]/1000, timezone.utc).isoformat() if rows else None,
        'end': datetime.fromtimestamp(rows[-1][0]/1000, timezone.utc).isoformat() if rows else None,
        'static_pmm_proxy': static,
        'inventory_skew_proxy': skewed,
        'delta_skew_minus_static': delta,
    }

report = {
    'source_system': 'hummingbot',
    'family': 'pure_market_making_inventory_skew',
    'classification_scope': 'RISK_OVERLAY_PROXY_NOT_EXECUTION_ALPHA',
    'research_only': True,
    'shadow_only': True,
    'factory_modified': False,
    'causality': 'quotes use previous closed bar; next bar only determines fill proxy',
    'fill_model': 'conservative OHLCV bar-cross proxy; if both bid and ask touched in same bar, both fills are skipped as sequence-ambiguous',
    'limitations': ['not order-book replay', 'no queue position', 'no maker rebate modeling', 'bar crossing is only a fill proxy'],
    'frozen': {
        'timeframe': TIMEFRAME,
        'target_bars': TARGET_BARS,
        'start_equity': START_EQUITY,
        'target_base_ratio': TARGET_BASE_RATIO,
        'order_value_frac': ORDER_VALUE_FRAC,
        'spread_per_side': SPREAD_PER_SIDE,
        'fee_per_fill': FEE_PER_FILL,
        'inventory_range_multiplier': INVENTORY_RANGE_MULTIPLIER,
    },
    'results': results,
}
print(json.dumps(report, indent=2, sort_keys=True))
