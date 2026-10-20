from pathlib import Path
import json
import csv
import sys
from datetime import datetime, timezone
from gate_btc_d50_data_review_reporting import documentary_adjudication, reporting_lines


def load_json(path):
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except Exception:
        return None


def safe(v, default="NOT_AVAILABLE"):
    return default if v is None else v


root = Path(sys.argv[1])
proj = Path(sys.argv[2])
state = Path(sys.argv[3])
downloads = Path(sys.argv[4])

now = datetime.now(timezone.utc).isoformat()

d50 = load_json(state / "D50_PROSPECTIVE_STATUS_V2.json")
audit = load_json(state / "D50_POSITION_AUDIT_LATEST.json")

# Documentary review only; AUTOPILOT V2 is not the audited V3.2 engine.
adjudication = documentary_adjudication(prospective_status=d50)

d100_path = (
    proj
    / "experiments"
    / "d100_universe_expansion_v1"
    / "state"
    / "D100_STATUS.json"
)
d100 = load_json(d100_path)

gov_snapshot = load_json(state / "GATE_BTC_GOVERNANCE_SNAPSHOT_LATEST.json")

# ------------------------------------------------------------
# 1. MASTER SIDECAR / POSITION AUDIT
# ------------------------------------------------------------

positions_csv = state / "D50_POSITION_AUDIT_LATEST.csv"
changes_csv = state / "D50_POSITION_CHANGES_LATEST.csv"

master_positions = []

if positions_csv.exists():
    with positions_csv.open("r", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            master_positions.append({
                "strategy": r.get("strategy"),
                "symbol": r.get("symbol"),
                "side": r.get("side"),
                "signed_weight": r.get("signed_weight"),
                "previous_signed_weight": r.get("previous_signed_weight"),
                "weight_change": r.get("weight_change"),
                "action": r.get("action"),
                "entry_price": r.get("entry_price"),
                "best_price": r.get("best_price"),
                "target_weight": r.get("target_weight"),
                "selection_reason": r.get("selection_reason"),
                "source_date": r.get("source_date"),
            })

master_sidecar = {
    "schema": "gate_btc.master_position_sidecar.v1",
    "created_at_utc": now,
    "current_documentary_adjudication": adjudication,
    "status": "PASS" if master_positions else "WARN_NO_POSITION_AUDIT",
    "d50_position_audit": {
        "source_status": safe(audit.get("status") if audit else None),
        "source_date": safe(audit.get("source_data_date") if audit else None),
        "positions": master_positions,
    },
    "governance": {
        "read_only": True,
        "engine_feed": False,
        "orders": 0,
        "capital": 0,
    }
}

master_path = state / "GATE_BTC_MASTER_POSITION_SIDECAR_LATEST.json"
master_path.write_text(
    json.dumps(master_sidecar, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

# ------------------------------------------------------------
# 2. LIVE VS FROZEN CLASSIFICATION
# ------------------------------------------------------------

live_frozen = []

def add_item(name, classification, source_date, reason):
    live_frozen.append({
        "component": name,
        "classification": classification,
        "source_date": source_date,
        "reason": reason,
    })

if d50:
    add_item(
        "D50_PROSPECTIVE",
        "LIVE",
        d50.get("latest_prospective_date")
        or d50.get("latest_date")
        or "FIELD_NOT_PUBLISHED",
        "prospective state advances only on admissible bars",
    )
else:
    add_item("D50_PROSPECTIVE", "UNKNOWN", "NONE", "status missing")

if audit:
    add_item(
        "D50_POSITION_AUDIT",
        "LIVE",
        audit.get("source_data_date", "FIELD_NOT_PUBLISHED"),
        "prospective reporting layer",
    )
else:
    add_item("D50_POSITION_AUDIT", "UNKNOWN", "NONE", "audit missing")

if d100:
    add_item(
        "D100_UNIVERSE_EXPANSION_V1",
        "FROZEN",
        "NOT_STARTED",
        "FROZEN_DORMANT until explicit activation after D50 gate",
    )
else:
    add_item("D100_UNIVERSE_EXPANSION_V1", "UNKNOWN", "NONE", "status missing")

live_frozen_path = state / "GATE_BTC_LIVE_FROZEN_STATUS_LATEST.csv"

with live_frozen_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "component",
            "classification",
            "source_date",
            "reason",
        ],
    )
    w.writeheader()
    w.writerows(live_frozen)

# ------------------------------------------------------------
# 3. CLOCK REGISTRY
# ------------------------------------------------------------

clocks = []

def clock(name, current, target, status, note=""):
    clocks.append({
        "clock": name,
        "current": current,
        "target": target,
        "status": status,
        "note": note,
    })

if d50:
    obs = d50.get("paired_prospective_observations")
    clock(
        "D50_PAIRED_PROSPECTIVE",
        safe(obs),
        safe(d50.get("next_checkpoint"), "UNKNOWN"),
        "LIVE",
        "Do not include retrospective backfill",
    )
else:
    clock("D50_PAIRED_PROSPECTIVE", "UNKNOWN", "UNKNOWN", "UNKNOWN")

if gov_snapshot:
    # Governance snapshot itself is not a scientific clock.
    clock(
        "GOVERNANCE",
        "PASS" if gov_snapshot.get("status") == "PASS" else "WARN",
        "PASS",
        "CONTROL",
        "Not a promotion clock",
    )

if d100:
    clock(
        "D100_PROSPECTIVE",
        d100.get("prospective_observations", 0),
        "TBD_AFTER_ACTIVATION",
        d100.get("status", "UNKNOWN"),
        "Must remain zero while FROZEN_DORMANT",
    )
else:
    clock("D100_PROSPECTIVE", "UNKNOWN", "TBD", "UNKNOWN")

clock_path = state / "GATE_BTC_CLOCK_REGISTRY_LATEST.csv"

with clock_path.open("w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(
        f,
        fieldnames=[
            "clock",
            "current",
            "target",
            "status",
            "note",
        ],
    )
    w.writeheader()
    w.writerows(clocks)

# ------------------------------------------------------------
# Human-readable report
# ------------------------------------------------------------

txt = downloads / "GATE_BTC_GOVERNANCE_MASTER_LATEST.txt"

lines = [
    "GATE BTC - GOVERNANCE / MASTER SIDECAR",
    f"CREATED_AT_UTC={now}",
    "",
    "=== POSITION AUDIT / MASTER ===",
    f"POSITION_ROWS={len(master_positions)}",
    f"POSITION_AUDIT_STATUS={safe(audit.get('status') if audit else None)}",
    f"POSITION_SOURCE_DATE={safe(audit.get('source_data_date') if audit else None)}",
    "",
    "=== LIVE VS FROZEN ===",
]

for x in live_frozen:
    lines.append(
        f"{x['component']} | {x['classification']} | "
        f"{x['source_date']} | {x['reason']}"
    )

lines += [
    "",
    "=== CLOCKS ===",
]

for c in clocks:
    lines.append(
        f"{c['clock']} | {c['current']}/{c['target']} | "
        f"{c['status']} | {c['note']}"
    )

lines += [
    "",
    "=== GOVERNANCE ===",
    "READ_ONLY=True",
    "ENGINE_FEED=False",
    "ENGINE_LOGIC_CHANGED=False",
    "ORDERS=0",
    "CAPITAL=0",
    "",
    f"MASTER_SIDECAR={master_path}",
    f"LIVE_FROZEN={live_frozen_path}",
    f"CLOCK_REGISTRY={clock_path}",
]

lines += ["", "=== D50 DOCUMENTARY DATA REVIEW ==="] + reporting_lines(adjudication)
txt.write_text("\n".join(lines), encoding="utf-8")

print("GOVERNANCE_MASTER=PASS")
print(f"MASTER_SIDECAR={master_path}")
print(f"LIVE_FROZEN={live_frozen_path}")
print(f"CLOCK_REGISTRY={clock_path}")
print(f"REPORT={txt}")

# Captured by RUN_DAILY Add-Line for the persistent daily report.
for review_line in reporting_lines(adjudication):
    print(review_line)
