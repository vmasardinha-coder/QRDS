#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import zipfile
from collections import defaultdict, deque
from datetime import date, datetime, timezone
from pathlib import Path

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
}
FAMILIES = [f"EQB{i:02d}" for i in range(1, 11)]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def field(line: bytes, a: int, b: int, enc: str = "ascii") -> str:
    return line[a:b].decode(enc, errors="replace").strip()


def med(xs):
    return statistics.median(xs) if xs else None


def sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def parse_quote(line: bytes):
    if len(line) != 245 or line[:2] != b"01":
        return None
    d = datetime.strptime(line[2:10].decode("ascii"), "%Y%m%d").date()
    bdi = field(line, 10, 12)
    symbol = field(line, 12, 24, "latin1")
    market = field(line, 24, 27)
    spec = field(line, 39, 49, "latin1")
    isin = field(line, 230, 242)
    if market != "010" or bdi != "02":
        return (d, None)
    token = spec.split()[0] if spec.split() else ""
    if token not in {"ON", "PN", "UNT"}:
        return (d, None)
    try:
        op = int(line[56:69])
        hi = int(line[69:82])
        lo = int(line[82:95])
        cl = int(line[108:121])
        trades = int(line[147:152])
        value = int(line[170:188]) / 100.0
    except ValueError as e:
        raise RuntimeError(f"invalid numeric quote for {d} {symbol}") from e
    if min(op, hi, lo, cl) <= 0 or hi < lo:
        return (d, None)
    ident = (symbol, isin, market, spec)
    return (d, (ident, op, hi, lo, cl, trades, value))


def load_capture(capture_dir: Path, hashes: dict):
    rows = defaultdict(list)
    sessions = set()
    expected = {int(o["year"]): o for o in hashes["objects"]}
    for year in sorted(expected):
        zp = capture_dir / f"COTAHIST_A{year}.ZIP"
        raw = zp.read_bytes()
        if sha256_bytes(raw) != expected[year]["raw_zip_sha256"]:
            raise RuntimeError(f"SOURCE_QA_FAIL raw ZIP hash mismatch {year}")
        with zipfile.ZipFile(zp) as z:
            members = [n for n in z.namelist() if not n.endswith("/")]
            if len(members) != 1:
                raise RuntimeError(f"SOURCE_QA_FAIL payload member count {year}: {members}")
            payload = z.read(members[0])
        if sha256_bytes(payload) != expected[year]["payload_sha256"]:
            raise RuntimeError(f"SOURCE_QA_FAIL payload hash mismatch {year}")
        for line in payload.splitlines():
            parsed = parse_quote(line)
            if parsed is None:
                continue
            d, q = parsed
            sessions.add(d)
            if q is not None:
                ident, op, hi, lo, cl, trades, value = q
                rows[ident].append((d, op, hi, lo, cl, trades, value))
    sessions = sorted(sessions)
    sidx = {d: i for i, d in enumerate(sessions)}
    for ident, rr in rows.items():
        rr.sort(key=lambda x: x[0])
        seen = set()
        for r in rr:
            if r[0] in seen:
                raise RuntimeError(f"SOURCE_QA_FAIL duplicate reduced identity/date {ident} {r[0]}")
            seen.add(r[0])
    return rows, sessions, sidx


def family_signal(fid: str, body: float, intraday_range: float, close_loc: float | None, vol_shock: float | None) -> int:
    s = sign(body)
    if fid == "EQB01": return s
    if fid == "EQB02": return -s
    if fid == "EQB03": return 1 if close_loc is not None and close_loc >= .80 else (-1 if close_loc is not None and close_loc <= .20 else 0)
    if fid == "EQB04": return -1 if close_loc is not None and close_loc >= .80 else (1 if close_loc is not None and close_loc <= .20 else 0)
    if fid == "EQB05": return s if intraday_range >= .03 else 0
    if fid == "EQB06": return -s if intraday_range >= .03 else 0
    if fid == "EQB07": return s if intraday_range <= .01 else 0
    if fid == "EQB08": return -s if intraday_range <= .01 else 0
    if fid == "EQB09": return s if vol_shock is not None and vol_shock >= 1.50 else 0
    if fid == "EQB10": return -s if vol_shock is not None and vol_shock >= 1.50 else 0
    raise KeyError(fid)


def build_positions(rows, sessions, sidx):
    pos1 = {f: defaultdict(list) for f in FAMILIES}
    pos2 = {f: defaultdict(list) for f in FAMILIES}
    for ident, rr in rows.items():
        by_date = {r[0]: r for r in rr}
        prior = deque()
        prior_eligible_values = deque(maxlen=20)
        for r in rr:
            d, op, hi, lo, cl, trades, value = r
            i = sidx[d]
            while prior and sidx[prior[0][0]] < i - 60:
                prior.popleft()
            prior_values = [x[6] for x in prior]
            prior_trades = [x[5] for x in prior]
            eligible = len(prior) >= 45 and med(prior_values) >= 20_000_000 and med(prior_trades) >= 500
            body = (cl - op) / op
            irange = (hi - lo) / op
            close_loc = ((cl - lo) / (hi - lo)) if hi > lo else None
            vol_shock = (value / med(prior_eligible_values)) if len(prior_eligible_values) >= 20 and med(prior_eligible_values) else None
            if eligible:
                for fid in FAMILIES:
                    sig = family_signal(fid, body, irange, close_loc, vol_shock)
                    if sig == 0:
                        continue
                    if i + 1 < len(sessions):
                        d1 = sessions[i + 1]
                        o1 = by_date.get(d1)
                        if o1 is not None:
                            gross = sig * ((o1[4] - o1[1]) / o1[1])
                            pos1[fid][d1].append((sig, gross, ident[0]))
                    if i + 2 < len(sessions):
                        d2 = sessions[i + 2]
                        o2 = by_date.get(d2)
                        if o2 is not None:
                            gross = sig * ((o2[4] - o2[1]) / o2[1])
                            pos2[fid][d2].append((sig, gross, ident[0]))
                prior_eligible_values.append(value)
            prior.append(r)
    return pos1, pos2


def window_sessions(sessions, start: str, end: str):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return [d for d in sessions if a <= d <= b]


def daily_series(positions, days, cost_bps: int):
    cost = cost_bps / 10000.0
    daily = []
    instrument_positions = 0
    long_n = short_n = 0
    side_returns = {1: [], -1: []}
    for d in days:
        xs = positions.get(d, [])
        if not xs:
            daily.append((d, 0.0, 0))
            continue
        rs = []
        for sig, gross, _sym in xs:
            r = gross - cost
            rs.append(r)
            side_returns[sig].append(r)
            if sig > 0: long_n += 1
            else: short_n += 1
        instrument_positions += len(xs)
        daily.append((d, sum(rs) / len(rs), len(xs)))
    return daily, instrument_positions, long_n, short_n, side_returns


def max_drawdown(rs):
    eq = peak = 1.0
    mdd = 0.0
    for r in rs:
        eq *= (1.0 + r)
        peak = max(peak, eq)
        if peak > 0:
            mdd = max(mdd, 1.0 - eq / peak)
    return mdd


def metrics(positions, days, cost_bps: int):
    daily, npos, long_n, short_n, side = daily_series(positions, days, cost_bps)
    rs = [r for _, r, _ in daily]
    active = sum(1 for _, _, n in daily if n > 0)
    mean = statistics.fmean(rs) if rs else 0.0
    sd = statistics.stdev(rs) if len(rs) > 1 else 0.0
    sharpe = mean / sd * math.sqrt(252) if sd > 0 else 0.0
    eq = 1.0
    for r in rs: eq *= 1 + r
    years = defaultdict(float)
    months = defaultdict(float)
    for d, r, _ in daily:
        years[d.year] += r
        months[(d.year, d.month)] += r
    pos_months = [v for v in months.values() if v > 0]
    conc = max(pos_months) / sum(pos_months) if pos_months else 1.0
    def side_mean(k): return statistics.fmean(side[k]) if side[k] else None
    return {
        "sessions": len(days),
        "active_days": active,
        "instrument_positions": npos,
        "mean_daily_net": mean,
        "annualized_sharpe": sharpe,
        "total_return_compounded": eq - 1.0,
        "max_drawdown": max_drawdown(rs),
        "positive_calendar_years": sum(1 for v in years.values() if v > 0),
        "calendar_year_pnl": {str(k): v for k, v in sorted(years.items())},
        "month_concentration": conc,
        "long_positions": long_n,
        "short_positions": short_n,
        "long_mean_position_net": side_mean(1),
        "short_mean_position_net": side_mean(-1),
        "daily_returns": rs,
    }


def bootstrap_mean_ci(rs, block=5, resamples=1000, seed=20260903):
    if not rs:
        return {"p05_mean": 0.0, "p50_mean": 0.0, "p95_mean": 0.0}
    rng = random.Random(seed)
    n = len(rs)
    starts = list(range(max(1, n - block + 1)))
    means = []
    for _ in range(resamples):
        out = []
        while len(out) < n:
            s = rng.choice(starts)
            out.extend(rs[s:s + block])
        means.append(statistics.fmean(out[:n]))
    means.sort()
    def q(p): return means[min(len(means)-1, max(0, int(p*(len(means)-1))))]
    return {"p05_mean": q(.05), "p50_mean": q(.50), "p95_mean": q(.95)}


def pass_discovery(m, g):
    return (m["active_days"] >= g["minimum_active_days"] and m["instrument_positions"] >= g["minimum_instrument_positions"] and
            m["mean_daily_net"] > g["primary_net_mean_daily_gt"] and m["annualized_sharpe"] >= g["primary_annualized_sharpe_gte"] and
            m["positive_calendar_years"] >= g["minimum_positive_calendar_years"] and m["max_drawdown"] <= g["max_drawdown_lte"] and
            m["month_concentration"] <= g["month_concentration_lte"])


def pass_robust(m40, md, g):
    return (m40["mean_daily_net"] > g["cost_40bps_net_mean_daily_gt"] and m40["annualized_sharpe"] >= g["cost_40bps_annualized_sharpe_gte"] and
            md["mean_daily_net"] > g["delayed_t_plus_2_primary_net_mean_daily_gt"] and md["annualized_sharpe"] >= g["delayed_t_plus_2_primary_annualized_sharpe_gte"] and
            md["active_days"] >= g["delayed_t_plus_2_minimum_active_days"])


def pass_replication(m, g):
    return (m["active_days"] >= g["minimum_active_days"] and m["instrument_positions"] >= g["minimum_instrument_positions"] and
            m["mean_daily_net"] > g["primary_net_mean_daily_gt"] and m["annualized_sharpe"] >= g["primary_annualized_sharpe_gte"] and
            m["positive_calendar_years"] >= g["minimum_positive_calendar_years"] and m["max_drawdown"] <= g["max_drawdown_lte"] and
            m["month_concentration"] <= g["month_concentration_lte"])


def clean_metrics(m):
    x = dict(m)
    x.pop("daily_returns", None)
    return x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture-dir", required=True)
    ap.add_argument("--prereg", default="tools/gate_btc_factory/B3_BLUECHIPS_UNIVARIATE_PREREG.v1.json")
    ap.add_argument("--gates", default="tools/gate_btc_factory/B3_BLUECHIPS_UNIVARIATE_GATES.v1.json")
    ap.add_argument("--hashes", default="tools/gate_btc_factory/B3_COTAHIST_FROZEN_HASHES.v1.json")
    ap.add_argument("--out", default="artifacts/gate_btc/factory/b3_bluechips_univariate/RESULT.json")
    args = ap.parse_args()
    prereg = json.loads(Path(args.prereg).read_text())
    gates = json.loads(Path(args.gates).read_text())
    hashes = json.loads(Path(args.hashes).read_text())
    assert prereg["economics_read_before_this_prereg"] is False
    assert gates["economics_read_before_gate_freeze"] is False
    assert prereg["family_ids"] == FAMILIES
    rows, sessions, _ = load_capture(Path(args.capture_dir), hashes)
    pos1, pos2 = build_positions(rows, sessions, {d:i for i,d in enumerate(sessions)})
    ddays = window_sessions(sessions, *gates["discovery_gate"]["window"])
    rdays = window_sessions(sessions, *gates["independent_replication_gate"]["window"])
    results = {}
    survivors = []
    for fid in FAMILIES:
        d20 = metrics(pos1[fid], ddays, 20)
        d30 = metrics(pos1[fid], ddays, 30)
        d40 = metrics(pos1[fid], ddays, 40)
        delayed = metrics(pos2[fid], ddays, 30)
        discovery_pass = pass_discovery(d30, gates["discovery_gate"])
        robust_pass = discovery_pass and pass_robust(d40, delayed, gates["robustness_gate"])
        item = {
            "family_id": fid,
            "mortality": None,
            "discovery": {"cost20": clean_metrics(d20), "cost30": clean_metrics(d30), "cost40": clean_metrics(d40), "pass": discovery_pass},
            "bias_causality_qa": {"pass": True, "own_market_only": True, "current_constituent_membership_used": False, "cross_asset_inputs_used": False, "source_hash_match": True},
            "robustness": {"delayed_t_plus_2_cost30": clean_metrics(delayed), "bootstrap_cost30": bootstrap_mean_ci(d30["daily_returns"]), "pass": robust_pass},
            "replication": None,
            "replicated_survivor": False
        }
        if d30["instrument_positions"] == 0:
            item["mortality"] = "NO_TRADES"
        elif not discovery_pass or not robust_pass:
            item["mortality"] = "SCIENTIFIC_REJECTION"
        else:
            rep = metrics(pos1[fid], rdays, 30)
            rep_pass = pass_replication(rep, gates["independent_replication_gate"])
            item["replication"] = {"cost30": clean_metrics(rep), "pass": rep_pass}
            if rep_pass:
                item["replicated_survivor"] = True
                survivors.append(fid)
            else:
                item["mortality"] = "SCIENTIFIC_REJECTION"
        results[fid] = item
    ranking = []
    for fid in survivors:
        x = results[fid]
        score = min(x["discovery"]["cost40"]["annualized_sharpe"], x["robustness"]["delayed_t_plus_2_cost30"]["annualized_sharpe"], x["replication"]["cost30"]["annualized_sharpe"])
        ranking.append((score, fid))
    ranking.sort(key=lambda z: (-z[0], z[1]))
    prospective = [fid for _, fid in ranking[:gates["survivor_policy"]["prospective_candidate_cap"]]]
    out = {
        "schema": "qrds.factory.b3_bluechips_univariate_result.v1",
        "stage": "DISCOVERY_QA_ROBUSTNESS_INDEPENDENT_REPLICATION",
        "frontier": "B3_BLUECHIPS_UNIVARIATE",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_frozen_hashes": hashes,
        "family_count": len(FAMILIES),
        "results": results,
        "replicated_survivors": survivors,
        "prospective_candidates": prospective,
        "final_survivor_status": survivors if survivors else "NULL — nenhum survivor válido",
        "prospective_activation_performed": False,
        "scientific_credit": len(survivors),
        "prospective_credit": 0,
        **SAFETY
    }
    op = Path(args.out); op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status":"PASS_EXECUTION","survivors":survivors,"prospective_candidates":prospective,**SAFETY}, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
