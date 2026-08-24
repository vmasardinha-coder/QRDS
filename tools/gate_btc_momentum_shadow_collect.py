#!/usr/bin/env python3
from __future__ import annotations

import argparse, csv, hashlib, io, json, math, sys, zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "migration" / "reporting"))
from qrds_momentum_m1 import compute as compute_m1  # noqa: E402

FREEZE = date.fromisoformat("2026-08-21")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_sha(payload: dict) -> str:
    body = {k: v for k, v in payload.items() if k != "snapshot_sha256"}
    return sha256_bytes((json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode())


def extract_prices(v2a_zip: Path, cutoff: str, out_csv: Path) -> dict:
    candidates = []
    with zipfile.ZipFile(v2a_zip) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"):
                continue
            raw = z.read(name)
            try:
                r = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
                fields = {str(x).strip().lower() for x in (r.fieldnames or [])}
            except Exception:
                continue
            if {"date", "symbol", "close_usd"}.issubset(fields):
                rows = list(r)
                candidates.append((name, raw, rows))
    if not candidates:
        raise SystemExit("no canonical V2A price CSV with date,symbol,close_usd")
    masters = [x for x in candidates if "master" in x[0].lower()]
    chosen_pool = masters or candidates
    if len(chosen_pool) != 1:
        raise SystemExit("ambiguous canonical V2A price CSV: " + ",".join(x[0] for x in chosen_pool))
    name, raw, rows = chosen_pool[0]
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    kept = 0
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["date", "asset", "close"])
        w.writeheader()
        for row in rows:
            d = str(row.get("date", ""))[:10]
            if not d or d > cutoff:
                continue
            symbol = str(row.get("symbol", "")).strip().upper()
            try:
                close = float(row.get("close_usd", ""))
            except Exception:
                continue
            if symbol and close > 0:
                w.writerow({"date": d, "asset": symbol, "close": close})
                kept += 1
    if kept == 0:
        raise SystemExit("canonical price extraction produced zero rows")
    return {"member": name, "member_sha256": sha256_bytes(raw), "rows": kept}


def _std(values):
    m = sum(values) / len(values)
    return math.sqrt(sum((x - m) ** 2 for x in values) / len(values))


def _median(values):
    s = sorted(values)
    n = len(s)
    if not n:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def compute_m2(prices_csv: Path, cutoff: str):
    by_asset = {}
    dates = set()
    with prices_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d, a, c = row["date"], row["asset"], float(row["close"])
            by_asset.setdefault(a, {})[d] = c
            dates.add(d)
    dates = sorted(dates)
    if cutoff not in dates:
        raise SystemExit(f"cutoff {cutoff} absent from canonical prices")
    idx = dates.index(cutoff)
    if idx < 30:
        raise SystemExit("M2 requires at least 31 calendar closes")
    window = dates[idx-30:idx+1]
    d14, d30 = dates[idx-14], dates[idx-30]
    if "BTC" not in by_asset:
        raise SystemExit("BTC is required for M2")

    def metrics(asset):
        px = by_asset[asset]
        if any(d not in px for d in window):
            return None
        r14 = px[cutoff] / px[d14] - 1
        r30 = px[cutoff] / px[d30] - 1
        daily30 = [px[window[i]] / px[window[i-1]] - 1 for i in range(1, len(window))]
        w14 = window[-15:]
        daily14 = [px[w14[i]] / px[w14[i-1]] - 1 for i in range(1, len(w14))]
        v14, v30 = _std(daily14), _std(daily30)
        if v14 <= 0 or v30 <= 0:
            return None
        return r14, r30, v14, v30

    btc = metrics("BTC")
    if btc is None:
        raise SystemExit("BTC lacks complete M2 history")
    br14, br30, bv14, bv30 = btc
    bsr14, bsr30 = br14 / bv14, br30 / bv30
    rows = []
    excluded = 0
    for asset in sorted(by_asset):
        m = metrics(asset)
        if m is None:
            excluded += 1
            continue
        r14, r30, v14, v30 = m
        sr14, sr30 = r14 / v14, r30 / v30
        rel14, rel30 = sr14 - bsr14, sr30 - bsr30
        imp = rel14 - rel30
        m2 = 0.65 * rel30 + 0.25 * rel14 + 0.10 * imp
        rows.append({"asset": asset, "r14": r14, "r30": r30, "vol14": v14, "vol30": v30,
                     "rel14": rel14, "rel30": rel30, "rel_impulse": imp,
                     "m2": m2, "display_score": max(-0.8, min(0.8, m2))})
    rows.sort(key=lambda x: x["m2"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank_m2"] = i
    scores = [x["m2"] for x in rows]
    summary = {
        "cutoff": cutoff,
        "universe_n": len(rows),
        "excluded_incomplete_history": excluded,
        "breadth_pct_m2_gt_zero": 100.0 * sum(x > 0 for x in scores) / len(scores),
        "median_m2": _median(scores),
        "cross_sectional_dispersion_m2": _std(scores),
        "status": "PROSPECTIVE_SHADOW_ONLY_NOT_APPROVED",
        "engine_feed": False, "orders": 0, "real_capital": 0,
    }
    return rows, summary


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--v2a-zip", type=Path, required=True)
    p.add_argument("--cutoff", required=True)
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    cutoff_day = date.fromisoformat(args.cutoff)
    if cutoff_day < FREEZE:
        raise SystemExit("pre-freeze cutoff forbidden for prospective ledger")

    work = args.output.parent / "momentum_prices.csv"
    source = extract_prices(args.v2a_zip, args.cutoff, work)
    m1_rows, m1_summary = compute_m1(work, args.cutoff)
    m2_rows, m2_summary = compute_m2(work, args.cutoff)

    args.ledger_dir.mkdir(parents=True, exist_ok=True)
    prior_files = sorted(p for p in args.ledger_dir.glob("*.json") if p.name != "STATUS.json")
    if prior_files:
        prior = json.loads(prior_files[-1].read_text(encoding="utf-8"))
        if prior.get("cutoff") >= args.cutoff and prior.get("cutoff") != args.cutoff:
            raise SystemExit("non-monotonic cutoff forbidden")
        if prior.get("cutoff") < args.cutoff:
            m1_summary["delta_breadth_pct_points"] = m1_summary["breadth_pct_m1_gt_zero"] - prior["m1"]["summary"]["breadth_pct_m1_gt_zero"]
            m2_summary["delta_breadth_pct_points"] = m2_summary["breadth_pct_m2_gt_zero"] - prior["m2"]["summary"]["breadth_pct_m2_gt_zero"]
    else:
        m1_summary["delta_breadth_pct_points"] = None
        m2_summary["delta_breadth_pct_points"] = None

    payload = {
        "schema": "gate-btc-momentum-m1m2-prospective-snapshot-v1",
        "cutoff": args.cutoff,
        "classification": "PROSPECTIVE_SHADOW",
        "source": {**source, "v2a_zip_sha256": sha256_file(args.v2a_zip)},
        "m1": {"summary": m1_summary, "rows": m1_rows},
        "m2": {"summary": m2_summary, "rows": m2_rows},
        "safety": {"research_only": True, "shadow_only": True, "not_approved": True,
                   "engine_feed": False, "allocation_weight": 0, "orders": 0, "real_capital": 0,
                   "automatic_tuning": False},
    }
    payload["snapshot_sha256"] = canonical_sha(payload)
    target = args.ledger_dir / f"{args.cutoff}.json"
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing.get("snapshot_sha256") != payload["snapshot_sha256"]:
            raise SystemExit("duplicate cutoff with different hash")
    else:
        target.write_text(rendered, encoding="utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({"cutoff": args.cutoff, "status": "PASS_PROSPECTIVE_SHADOW", "snapshot_sha256": payload["snapshot_sha256"], "m1_n": len(m1_rows), "m2_n": len(m2_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
