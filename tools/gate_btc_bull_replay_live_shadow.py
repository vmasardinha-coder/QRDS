#!/usr/bin/env python3
"""Append-only common live scoreboard for GATE BTC research portfolios.

Consumes exact V2A and Delta ZIPs from a successful Daily Research artifact.
No private APIs, no orders, no capital, no frozen-engine changes.
"""
from __future__ import annotations

import argparse, csv, hashlib, io, json, zipfile
from datetime import date, timedelta
from pathlib import Path
from typing import Any

REQUIRED_V2A = ("Victor_proxy", "BTC_puro", "BTC_ETH_70_30", "QOS_Moderada", "QOS_Ultra")
REQUIRED_DELTA = ("Delta_LS_50_50", "Delta_LS_50_50_StopVol", "Delta_LS_70_30", "Delta_LS_70_30_StopVol")
ZERO_HASH = "0" * 64

class LiveShadowError(RuntimeError):
    pass

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()

def d(s: str) -> date:
    return date.fromisoformat(s)

def read_json_zip(z: zipfile.ZipFile, suffix: str) -> dict:
    names = [n for n in z.namelist() if n.endswith(suffix)]
    if len(names) != 1:
        raise LiveShadowError(f"missing/ambiguous {suffix}: {names}")
    return json.loads(z.read(names[0]).decode("utf-8-sig"))

def read_csv_zip(z: zipfile.ZipFile, suffix: str) -> list[dict[str, str]]:
    names = [n for n in z.namelist() if n.endswith(suffix)]
    if len(names) != 1:
        raise LiveShadowError(f"missing/ambiguous {suffix}: {names}")
    return list(csv.DictReader(io.StringIO(z.read(names[0]).decode("utf-8-sig"))))

def load_contract(path: Path) -> dict:
    c = json.loads(path.read_text(encoding="utf-8"))
    if c.get("schema") != "gate_btc.bull_replay_live_shadow.v1":
        raise LiveShadowError("wrong schema")
    s = c.get("safety", {})
    required = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "methodology_changes_to_frozen_engines": 0,
    }
    for k, v in required.items():
        if s.get(k) != v:
            raise LiveShadowError(f"unsafe contract {k}")
    if tuple(c["series"]["v2a_published_equity"]) != REQUIRED_V2A:
        raise LiveShadowError("V2A series changed")
    if tuple(c["series"]["delta_published_daily"]) != REQUIRED_DELTA:
        raise LiveShadowError("Delta series changed")
    if d(c["anchor_date"]) + timedelta(days=1) != d(c["first_return_date"]):
        raise LiveShadowError("anchor/first date mismatch")
    return c

def parse_source(v2a_zip: Path, delta_zip: Path) -> dict:
    vb = v2a_zip.read_bytes()
    db = delta_zip.read_bytes()
    with zipfile.ZipFile(io.BytesIO(vb)) as vz, zipfile.ZipFile(io.BytesIO(db)) as dz:
        vm = read_json_zip(vz, "outputs/v2a_run_manifest.json")
        dm = read_json_zip(dz, "outputs/delta_v11_run_manifest.json")
        asof = str(vm.get("data_as_of"))
        if asof != str(dm.get("data_as_of")):
            raise LiveShadowError(f"matched-close mismatch V2A={asof} Delta={dm.get('data_as_of')}")
        eq = read_csv_zip(vz, "outputs/qos_v2a_equity_curves.csv")
        trades = read_csv_zip(vz, "outputs/qos_v2a_buy_sell_log.csv")
        dr = read_csv_zip(dz, "outputs/delta_daily_returns.csv")
    return {
        "data_as_of": asof,
        "v2a_manifest": vm,
        "delta_manifest": dm,
        "equity": eq,
        "trades": trades,
        "delta_returns": dr,
        "v2a_sha256": sha256_bytes(vb),
        "delta_sha256": sha256_bytes(db),
    }

def exact_equity(rows: list[dict[str, str]], strategy: str, day: str) -> float:
    vals = [float(r["equity_brl"]) for r in rows if r.get("strategy") == strategy and r.get("date") == day]
    if len(vals) != 1:
        raise LiveShadowError(f"equity {strategy} {day}: {len(vals)} rows")
    return vals[0]

def v2a_cost(rows: list[dict[str, str]], strategy: str, day: str) -> float:
    vals = [float(r.get("cost_fraction") or 0) for r in rows if r.get("strategy") == strategy and r.get("execution_date") == day]
    if len(vals) > 1:
        raise LiveShadowError(f"multiple V2A cost rows {strategy} {day}")
    return vals[0] if vals else 0.0

def exact_delta(rows: list[dict[str, str]], strategy: str, day: str) -> tuple[float, float]:
    vals = [r for r in rows if r.get("strategy") == strategy and r.get("date") == day]
    if len(vals) != 1:
        raise LiveShadowError(f"delta {strategy} {day}: {len(vals)} rows")
    return float(vals[0]["gross_return"]), float(vals[0]["net_return"])

def load_ledger(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write_ledger(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "date", "series", "source_family", "gross_return", "net_return", "gross_nav", "net_nav",
        "source_run_id", "source_data_as_of", "source_v2a_sha256", "source_delta_sha256", "prev_hash", "row_hash",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

def hash_row(row: dict[str, Any]) -> str:
    core = {k: row[k] for k in row if k != "row_hash"}
    return sha256_bytes(canonical(core))

def metrics(rows: list[dict[str, Any]]) -> dict:
    out = {}
    for name in (*REQUIRED_V2A, *REQUIRED_DELTA):
        rr = [r for r in rows if r["series"] == name]
        if not rr:
            continue
        nav = [float(r["net_nav"]) for r in rr]
        peak = nav[0]
        mdd = 0.0
        for x in nav:
            peak = max(peak, x)
            mdd = min(mdd, x / peak - 1)
        out[name] = {
            "observations": len(rr),
            "net_nav": nav[-1],
            "return_since_start": nav[-1] - 1,
            "max_drawdown": mdd,
        }
    return out

def process(contract_path: Path, v2a_zip: Path, delta_zip: Path, runtime_dir: Path, source_run_id: str) -> dict:
    c = load_contract(contract_path)
    src = parse_source(v2a_zip, delta_zip)
    asof = d(src["data_as_of"])
    anchor = d(c["anchor_date"])
    first = d(c["first_return_date"])
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = runtime_dir / "DAILY_LEDGER.csv"
    status_path = runtime_dir / "STATUS.json"
    anchor_path = runtime_dir / "ANCHOR.json"
    existing = load_ledger(ledger_path)

    if asof < anchor:
        return {"status": "WAITING_ANCHOR_DATE", "data_as_of": asof.isoformat(), "runtime_write": False}

    if not anchor_path.exists():
        if asof != anchor:
            raise LiveShadowError(f"missed immutable anchor: expected {anchor}, got {asof}; no backfill")
        anchors = {}
        for s in REQUIRED_V2A:
            anchors[s] = exact_equity(src["equity"], s, anchor.isoformat())
        for s in REQUIRED_DELTA:
            vals = [r for r in src["delta_returns"] if r.get("strategy") == s and r.get("date") == anchor.isoformat()]
            if len(vals) != 1:
                raise LiveShadowError(f"missing Delta anchor row {s} {anchor}")
            anchors[s] = float(vals[0]["equity"])
        ap = {
            "schema": "gate_btc.bull_replay_live_shadow.anchor.v1",
            "anchor_date": anchor.isoformat(),
            "first_return_date": first.isoformat(),
            "source_run_id": str(source_run_id),
            "source_data_as_of": src["data_as_of"],
            "source_v2a_sha256": src["v2a_sha256"],
            "source_delta_sha256": src["delta_sha256"],
            "published_engine_equity_reference": anchors,
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
        }
        anchor_path.write_text(json.dumps(ap, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        st = {
            "status": "ARMED_WAITING_FIRST_RETURN",
            "data_as_of": src["data_as_of"],
            "anchor": ap,
            "macroquant": "WAITING_CONTEMPORANEOUS_INDEPENDENT_FEED",
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders_generated": 0,
            "real_capital_used": 0,
        }
        status_path.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return {"status": st["status"], "data_as_of": src["data_as_of"], "runtime_write": True}

    anchor_obj = json.loads(anchor_path.read_text(encoding="utf-8"))
    if asof == anchor:
        if anchor_obj["source_data_as_of"] != src["data_as_of"]:
            raise LiveShadowError("anchor mutation")
        return {"status": "ARMED_WAITING_FIRST_RETURN", "data_as_of": src["data_as_of"], "runtime_write": False}

    existing_dates = sorted({d(r["date"]) for r in existing})
    expected = first if not existing_dates else existing_dates[-1] + timedelta(days=1)
    if asof < expected:
        return {"status": "ALREADY_CURRENT", "data_as_of": src["data_as_of"], "runtime_write": False}
    if asof != expected:
        raise LiveShadowError(f"daily gap: expected {expected}, got {asof}; no backfill")

    prev_day = asof - timedelta(days=1)
    prev_hash = existing[-1]["row_hash"] if existing else ZERO_HASH
    prev_nav = {s: (1.0, 1.0) for s in (*REQUIRED_V2A, *REQUIRED_DELTA)}
    if existing:
        last = existing_dates[-1].isoformat()
        for s in prev_nav:
            rr = [r for r in existing if r["date"] == last and r["series"] == s]
            if len(rr) != 1:
                raise LiveShadowError(f"prior ledger missing {s} {last}")
            prev_nav[s] = (float(rr[0]["gross_nav"]), float(rr[0]["net_nav"]))

    new = []
    for s in REQUIRED_V2A:
        e0 = exact_equity(src["equity"], s, prev_day.isoformat())
        e1 = exact_equity(src["equity"], s, asof.isoformat())
        nr = e1 / e0 - 1
        cost = v2a_cost(src["trades"], s, asof.isoformat())
        if not (0 <= cost < 1):
            raise LiveShadowError(f"bad cost {s} {asof}: {cost}")
        gr = (1 + nr) / (1 - cost) - 1 if cost else nr
        gprev, nprev = prev_nav[s]
        row = {
            "date": asof.isoformat(),
            "series": s,
            "source_family": "V2A_PUBLISHED_EQUITY",
            "gross_return": f"{gr:.12g}",
            "net_return": f"{nr:.12g}",
            "gross_nav": f"{gprev * (1 + gr):.12g}",
            "net_nav": f"{nprev * (1 + nr):.12g}",
            "source_run_id": str(source_run_id),
            "source_data_as_of": src["data_as_of"],
            "source_v2a_sha256": src["v2a_sha256"],
            "source_delta_sha256": src["delta_sha256"],
            "prev_hash": prev_hash,
        }
        row["row_hash"] = hash_row(row)
        prev_hash = row["row_hash"]
        new.append(row)

    for s in REQUIRED_DELTA:
        gr, nr = exact_delta(src["delta_returns"], s, asof.isoformat())
        gprev, nprev = prev_nav[s]
        row = {
            "date": asof.isoformat(),
            "series": s,
            "source_family": "DELTA_PUBLISHED_DAILY",
            "gross_return": f"{gr:.12g}",
            "net_return": f"{nr:.12g}",
            "gross_nav": f"{gprev * (1 + gr):.12g}",
            "net_nav": f"{nprev * (1 + nr):.12g}",
            "source_run_id": str(source_run_id),
            "source_data_as_of": src["data_as_of"],
            "source_v2a_sha256": src["v2a_sha256"],
            "source_delta_sha256": src["delta_sha256"],
            "prev_hash": prev_hash,
        }
        row["row_hash"] = hash_row(row)
        prev_hash = row["row_hash"]
        new.append(row)

    all_rows = [*existing, *new]
    write_ledger(ledger_path, all_rows)
    m = metrics(all_rows)
    rank = sorted(({"series": k, **v} for k, v in m.items()), key=lambda x: x["net_nav"], reverse=True)
    st = {
        "schema": "gate_btc.bull_replay_live_shadow.status.v1",
        "status": "LIVE_DIAGNOSTIC_ACTIVE",
        "data_as_of": src["data_as_of"],
        "anchor_date": anchor.isoformat(),
        "first_return_date": first.isoformat(),
        "observed_days": len(sorted({r["date"] for r in all_rows})),
        "leaderboard_descriptive_only": rank,
        "macroquant": "WAITING_CONTEMPORANEOUS_INDEPENDENT_FEED",
        "qos_three_track_first_signal": "2026-08-31",
        "does_not_replace_formal_prospective_tests": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "ledger_tip_hash": prev_hash,
    }
    status_path.write_text(json.dumps(st, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "status": st["status"],
        "data_as_of": src["data_as_of"],
        "runtime_write": True,
        "observed_days": st["observed_days"],
        "leader": rank[0]["series"] if rank else None,
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--contract", type=Path, required=True)
    p.add_argument("--v2a-zip", type=Path, required=True)
    p.add_argument("--delta-zip", type=Path, required=True)
    p.add_argument("--runtime-dir", type=Path, required=True)
    p.add_argument("--source-run-id", required=True)
    a = p.parse_args()
    print(json.dumps(process(a.contract, a.v2a_zip, a.delta_zip, a.runtime_dir, a.source_run_id), indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
