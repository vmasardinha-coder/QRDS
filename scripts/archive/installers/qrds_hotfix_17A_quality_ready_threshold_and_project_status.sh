#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase17_consensus_quality_drift_monitor_pack"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

cd "$ROOT"

echo "[HOTFIX 17A] Patching Phase 17 test-threshold bug and adding project status doc..."

python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase17_consensus_quality_drift_monitor_pack.py")
if not path.exists():
    raise SystemExit(f"Missing Phase 17 file: {path}")

text = path.read_text(encoding="utf-8")

text = text.replace(
    "def _analyze_coin(root: Path, coin: str, outlier_threshold_bps: float) -> dict[str, Any]:",
    "def _analyze_coin(root: Path, coin: str, outlier_threshold_bps: float, min_rows_per_coin: int = DEFAULT_MIN_ROWS_PER_COIN) -> dict[str, Any]:",
)

text = text.replace(
    'summary["ready"] = bool(rows) and summary["rows"] >= DEFAULT_MIN_ROWS_PER_COIN and summary["source_count_min"] >= 3',
    'summary["ready"] = bool(rows) and summary["rows"] >= min_rows_per_coin and summary["source_count_min"] >= 3',
)

text = text.replace(
    "coin_summaries = [_analyze_coin(root, coin, outlier_deviation_bps) for coin in COINS]",
    "coin_summaries = [_analyze_coin(root, coin, outlier_deviation_bps, min_rows_per_coin) for coin in COINS]",
)

path.write_text(text, encoding="utf-8")
print("[HOTFIX 17A] Phase 17 threshold patch OK.")
PY

cat > "$PROJECT/tests/regression/test_phase17_quality_ready_uses_configured_min_rows.py" <<'PY'
import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase17_consensus_quality_drift_monitor_pack import build_phase17_consensus_quality_drift_monitor_pack


def _write_phase16_index(root: Path) -> None:
    p = root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"gate_answer": "READY", "consensus_baseline_ready": True}), encoding="utf-8")


def _write_consensus(path: Path, coin: str, rows: int = 6) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "coin",
        "source_count",
        "ready_sources",
        "consensus_close_median",
        "consensus_close_mean",
        "source_close_min",
        "source_close_max",
        "source_dispersion_bps",
        "BINANCE_SPOT_close",
        "BINANCE_SPOT_deviation_bps",
        "HYPERLIQUID_PERP_close",
        "HYPERLIQUID_PERP_deviation_bps",
        "OKX_SWAP_close",
        "OKX_SWAP_deviation_bps",
        "research_only",
        "source",
        "canonical_write",
        "trading_signal_generated",
        "recommendation_generated",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(rows):
            price = 100 + i
            w.writerow(
                {
                    "timestamp": f"2026-01-01T0{i}:00:00Z",
                    "coin": coin,
                    "source_count": 3,
                    "ready_sources": "BINANCE_SPOT|HYPERLIQUID_PERP|OKX_SWAP",
                    "consensus_close_median": price,
                    "consensus_close_mean": price,
                    "source_close_min": price - 0.05,
                    "source_close_max": price + 0.05,
                    "source_dispersion_bps": 10,
                    "BINANCE_SPOT_close": price,
                    "BINANCE_SPOT_deviation_bps": 0,
                    "HYPERLIQUID_PERP_close": price + 0.01,
                    "HYPERLIQUID_PERP_deviation_bps": 1,
                    "OKX_SWAP_close": price - 0.01,
                    "OKX_SWAP_deviation_bps": -1,
                    "research_only": "true",
                    "source": "QRDS_MULTISOURCE_CONSENSUS_RESEARCH_ONLY",
                    "canonical_write": "false",
                    "trading_signal_generated": "false",
                    "recommendation_generated": "false",
                }
            )


def test_phase17_quality_ready_uses_configured_min_rows(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write_phase16_index(root)
    for coin in ["BTC", "ETH", "SOL"]:
        _write_consensus(
            root / "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/consensus" / f"{coin.lower()}_multisource_consensus_1h.csv",
            coin,
            rows=6,
        )

    result = build_phase17_consensus_quality_drift_monitor_pack(tmp_path / "out", root, min_rows_per_coin=6)
    payload = result["payload"]

    assert payload["gate_answer"] == "PHASE17_CONSENSUS_QUALITY_DRIFT_MONITOR_READY_RESEARCH_ONLY"
    assert payload["quality_drift_monitor_ready"] is True
    assert payload["min_quality_rows_per_coin"] == 6
    assert payload["quality_rows_total"] == 18
PY

echo "[HOTFIX 17A] Running targeted Phase 17 tests..."
cd "$PROJECT"
pytest -q \
  tests/regression/test_phase17_quality_ready_uses_configured_min_rows.py \
  tests/unit/test_phase17_consensus_quality_drift_monitor_pack.py \
  tests/integration/test_phase17_consensus_quality_drift_monitor_pack_cli.py \
  tests/regression/test_phase17_consensus_quality_missing_consensus_needs_review.py

echo "[HOTFIX 17A] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 17A] Generating Phase 17 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase17_consensus_quality_drift_monitor_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path

root = Path(".")
idx_path = root / "crypto_decision_lab/artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json"
if not idx_path.exists():
    raise SystemExit("Phase 17 index missing.")

d = json.loads(idx_path.read_text(encoding="utf-8"))

print("[HOTFIX 17A] Phase 17 summary:")
for k in [
    "gate_answer",
    "station",
    "quality_drift_monitor_ready",
    "data_nature",
    "phase16_consensus_baseline_ready",
    "coins",
    "coins_count",
    "source_ids",
    "quality_rows_total",
    "min_quality_rows_per_coin",
    "max_p95_dispersion_bps",
    "max_source_outlier_rate",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_quality_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")

print("[HOTFIX 17A] Coin quality summaries:")
for s in d.get("payload", {}).get("coin_quality_summaries", []):
    print(f"{s['coin']}: rows={s['rows']} disp_mean={s['dispersion_bps_mean']} disp_p95={s['dispersion_bps_p95']} disp_p99={s['dispersion_bps_p99']} max_outlier_rate={s['max_source_outlier_rate']} ann_vol={s['consensus_ann_vol_research']} max_dd={s['consensus_max_drawdown_research']} ready={s['ready']}")

# Bundled project status doc update.
status_path = root / "crypto_decision_lab/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
status_path.parent.mkdir(parents=True, exist_ok=True)

phase_paths = {
    "Phase 12 Binance public data certification": "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json",
    "Phase 13 Binance research backtest baseline": "crypto_decision_lab/artifacts/phase13_research_backtest_baseline_pack/phase13_research_backtest_baseline_pack_index.json",
    "Phase 13 Hyperliquid public adapter": "crypto_decision_lab/artifacts/phase13_hyperliquid_public_data_adapter_pack/phase13_hyperliquid_public_data_adapter_pack_index.json",
    "Phase 13 Binance x Hyperliquid comparison": "crypto_decision_lab/artifacts/phase13_binance_hyperliquid_source_comparison_pack/phase13_binance_hyperliquid_source_comparison_pack_index.json",
    "Phase 14 Bybit public adapter": "crypto_decision_lab/artifacts/phase14_bybit_public_data_adapter_pack/phase14_bybit_public_data_adapter_pack_index.json",
    "Phase 14 OKX public adapter": "crypto_decision_lab/artifacts/phase14_okx_public_data_adapter_pack/phase14_okx_public_data_adapter_pack_index.json",
    "Phase 15 Multi-source trust registry": "crypto_decision_lab/artifacts/phase15_multisource_trust_registry_comparison_pack/phase15_multisource_trust_registry_comparison_pack_index.json",
    "Phase 16 Multi-source consensus baseline": "crypto_decision_lab/artifacts/phase16_multisource_consensus_baseline_pack/phase16_multisource_consensus_baseline_pack_index.json",
    "Phase 17 Consensus quality drift monitor": "crypto_decision_lab/artifacts/phase17_consensus_quality_drift_monitor_pack/phase17_consensus_quality_drift_monitor_pack_index.json",
}

lines = [
    "# QRDS/QOS Gate BTC — Project Status",
    "",
    f"Updated at: {d.get('generated_at')}",
    "",
    "## Current posture",
    "",
    "- Mode: `INTERACTIVE_RESEARCH_ONLY`",
    "- Operational status: `BLOCKED_RESEARCH_ONLY`",
    "- No trading signals, recommendations, allocation decisions, safe-apply, real orders, or canonical promotion.",
    "- Canonical data writes remain `0`.",
    "",
    "## Source/data status",
    "",
    "| Area | Gate | Ready/Status | Rows/Notes |",
    "|---|---|---:|---|",
]

for label, rel in phase_paths.items():
    p = root / rel
    try:
        item = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        item = {}
    gate = item.get("gate_answer", "MISSING")
    ready = (
        item.get("public_data_research_ready")
        or item.get("backtest_baseline_ready")
        or item.get("hyperliquid_adapter_ready")
        or item.get("source_comparison_ready")
        or item.get("bybit_adapter_ready")
        or item.get("okx_adapter_ready")
        or item.get("trust_registry_ready")
        or item.get("consensus_baseline_ready")
        or item.get("quality_drift_monitor_ready")
        or False
    )
    rows = (
        item.get("certified_public_rows")
        or item.get("rows_analyzed")
        or item.get("hyperliquid_rows_total")
        or item.get("bybit_rows_total")
        or item.get("okx_rows_total")
        or item.get("consensus_rows_total")
        or item.get("quality_rows_total")
        or item.get("min_common_timestamps")
        or ""
    )
    notes = []
    if item.get("endpoint_access_status"):
        notes.append(str(item.get("endpoint_access_status")))
    if item.get("ready_sources"):
        notes.append("ready_sources=" + ",".join(item.get("ready_sources", [])))
    if item.get("excluded_pending_sources"):
        notes.append("excluded=" + ",".join(item.get("excluded_pending_sources", [])))
    rows_notes = str(rows)
    if notes:
        rows_notes += " / " + " / ".join(notes)
    lines.append(f"| {label} | `{gate}` | `{ready}` | {rows_notes} |")

lines += [
    "",
    "## Current approved stack",
    "",
    "1. Binance public spot data certified.",
    "2. Binance research backtest baseline certified.",
    "3. Hyperliquid public perps adapter certified.",
    "4. Binance x Hyperliquid source comparison certified.",
    "5. OKX public swap adapter certified when depth extension is ready in the local run.",
    "6. Bybit adapter implemented but pending external/IP access.",
    "7. Multi-source trust registry certified with Bybit pending.",
    "8. Multi-source consensus baseline certified.",
    "9. Consensus quality/drift monitor status follows latest Phase 17 gate.",
    "",
    "## Next technical direction",
    "",
    "- If Phase 17 is READY: build research feature layer / regime diagnostics on consensus data.",
    "- If Phase 17 is NEEDS_REVIEW: inspect dispersion/outlier gates before adding new feature layers.",
    "- Keep documentation updates bundled into larger sprint/hotfix packages instead of separate packages.",
    "",
]
status_path.write_text("\n".join(lines), encoding="utf-8")
print(f"[HOTFIX 17A] Updated project status doc: {status_path}")
PY

echo "[HOTFIX 17A] Archiving root installers if present..."
cd "$ROOT"
mkdir -p scripts/archive/installers
for f in \
  "qrds_hotfix_17A_quality_ready_threshold_and_project_status.sh" \
  "qrds_hotfix_17A_quality_ready_threshold_and_project_status (1).sh" \
  "qrds_sprint_17A_to_17R_consensus_quality_drift_monitor_pack.sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[HOTFIX 17A] Archived $f"
  fi
done

echo "[HOTFIX 17A] Committing changes..."
git add -A
git commit -m "Fix Phase 17 quality threshold and update project status" || true
git push || true

echo "[HOTFIX 17A] Final status:"
git status --short
