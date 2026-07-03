#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then ROOT="/workspaces/QRDS"; fi
PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

echo "[HOTFIX 13A] Patching normalizer to remove stale normalized JSONL artifacts before each run..."
python - <<'PY'
from pathlib import Path

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase11_offline_source_normalizer_pack.py")
text = path.read_text(encoding="utf-8")

old = '    nd=out/"normalized"; nd.mkdir(parents=True, exist_ok=True)\n    summaries=[]; outputs=[]\n'
new = (
'    nd=out/"normalized"; nd.mkdir(parents=True, exist_ok=True)\n'
'    # Clear stale normalized files from prior modes/runs before writing current outputs.\n'
'    # This prevents fallback/sample artifacts from being mixed with public inbox data.\n'
'    for old_file in nd.glob("*.jsonl"):\n'
'        old_file.unlink()\n'
'    summaries=[]; outputs=[]\n'
)
if old in text and "Clear stale normalized files from prior modes/runs" not in text:
    text = text.replace(old, new)

old2 = '    norm_dir = out / "normalized"\n    norm_dir.mkdir(parents=True, exist_ok=True)\n    summaries: list[dict[str, Any]] = []\n    outputs: list[dict[str, Any]] = []\n'
new2 = (
'    norm_dir = out / "normalized"\n'
'    norm_dir.mkdir(parents=True, exist_ok=True)\n'
'    # Clear stale normalized files from prior modes/runs before writing current outputs.\n'
'    # This prevents fallback/sample artifacts from being mixed with public inbox data.\n'
'    for old_file in norm_dir.glob("*.jsonl"):\n'
'        old_file.unlink()\n'
'    summaries: list[dict[str, Any]] = []\n'
'    outputs: list[dict[str, Any]] = []\n'
)
if old2 in text and "Clear stale normalized files from prior modes/runs" not in text:
    text = text.replace(old2, new2)

if "Clear stale normalized files from prior modes/runs" not in text:
    raise SystemExit("Could not patch normalizer cleanup block.")

path.write_text(text, encoding="utf-8")
PY

echo "[HOTFIX 13A] Patching Phase 13 discovery to use current normalizer manifest outputs first..."
python - <<'PY'
from pathlib import Path
import re

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase13_research_backtest_baseline_pack.py")
text = path.read_text(encoding="utf-8")

new_func = '''def _discover_rows(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    paths_checked: list[str] = []
    rows: list[dict[str, Any]] = []

    # Prefer the latest normalizer manifest outputs over directory globbing.
    # This prevents stale normalized artifacts from prior fallback/sample modes
    # from being included in Phase 13 metrics.
    normalizer_index = root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "phase11_offline_source_normalizer_pack_index.json"
    try:
        index = json.loads(normalizer_index.read_text(encoding="utf-8"))
        payload = index.get("payload") if isinstance(index.get("payload"), dict) else {}
        outputs = payload.get("normalization_outputs") if isinstance(payload.get("normalization_outputs"), list) else []
        for item in outputs:
            path_value = item.get("path") if isinstance(item, dict) else None
            if not path_value:
                continue
            p = Path(path_value)
            if p.exists() and p.suffix.lower() == ".jsonl":
                paths_checked.append(str(p))
                rows.extend(_read_jsonl(p))
        if rows:
            return rows, paths_checked
    except Exception:
        pass

    preferred_dirs = [
        root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "normalized",
        root / "crypto_decision_lab" / "artifacts" / "phase10_offline_sample_intake_promotion_pack" / "validated_staging",
    ]
    for directory in preferred_dirs:
        if directory.exists():
            files = sorted([p for p in directory.glob("*.jsonl") if p.is_file()])
            if files:
                for p in files:
                    paths_checked.append(str(p))
                    rows.extend(_read_jsonl(p))
                if rows:
                    return rows, paths_checked

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    if inbox.exists():
        files = sorted(inbox.glob("*_binance_public_klines_1h.csv"))
        for p in files:
            paths_checked.append(str(p))
            rows.extend(_read_csv(p))

    return rows, paths_checked
'''

pattern = r'def _discover_rows\(root: Path\) -> tuple\[list\[dict\[str, Any\]\], list\[str\]\]:\n(?:    .*\n)+?\n    return rows, paths_checked\n'
if re.search(pattern, text):
    text = re.sub(pattern, new_func + "\n", text)
elif "Prefer the latest normalizer manifest outputs" not in text:
    raise SystemExit("Could not find _discover_rows function to patch.")

path.write_text(text, encoding="utf-8")
PY

cat > "$PROJECT/tests/regression/test_phase13_backtest_excludes_stale_normalized_artifacts.py" <<'PY'
import json
from pathlib import Path

from crypto_decision_lab.reports.phase13_research_backtest_baseline_pack import build_phase13_research_backtest_baseline_pack


def _write_jsonl(path: Path, symbol: str, rows: int, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in range(rows):
        price = 100 + i
        lines.append(
            json.dumps(
                {
                    "timestamp": f"2026-01-01T{i:02d}:00:00Z",
                    "open": price,
                    "high": price + 1,
                    "low": price - 1,
                    "close": price + 0.5,
                    "volume": 1000 + i,
                    "symbol": symbol,
                    "interval": "1h",
                    "source": source,
                },
                sort_keys=True,
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_phase13_backtest_uses_normalizer_manifest_not_stale_glob(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    norm_dir = root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "normalized"

    current_paths = []
    for symbol in ["BTC-USDT", "ETH-USDT", "SOL-USDT"]:
        safe = symbol.lower().replace("-", "_")
        p = norm_dir / f"{safe}_current_public.jsonl"
        _write_jsonl(p, symbol, 5, "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY")
        current_paths.append(str(p))

    _write_jsonl(norm_dir / "btc_usdt_stale_fallback.jsonl", "BTC-USDT", 5, "SAMPLE_FALLBACK_RESEARCH_ONLY")

    index = root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "phase11_offline_source_normalizer_pack_index.json"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE11_OFFLINE_SOURCE_NORMALIZER_READY_WITH_INBOX_FILES_RESEARCH_ONLY",
                "payload": {
                    "normalization_outputs": [{"path": p, "rows": 5} for p in current_paths],
                    "rows_normalized": 15,
                },
            }
        ),
        encoding="utf-8",
    )

    cert = root / "crypto_decision_lab" / "artifacts" / "phase12_public_data_research_readiness_certification_pack" / "phase12_public_data_research_readiness_certification_pack_index.json"
    cert.parent.mkdir(parents=True, exist_ok=True)
    cert.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE12_PUBLIC_DATA_RESEARCH_READY_CERTIFIED_RESEARCH_ONLY",
                "public_data_research_ready": True,
                "public_rows_total": 15,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )

    accept = root / "crypto_decision_lab" / "artifacts" / "phase11_data_drop_acceptance_pipeline_pack" / "phase11_data_drop_acceptance_pipeline_pack_index.json"
    accept.parent.mkdir(parents=True, exist_ok=True)
    accept.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE11_DATA_DROP_ACCEPTANCE_PIPELINE_READY_INBOX_DATA_RESEARCH_ONLY",
                "data_drop_mode": "INBOX_DATA",
                "rows_normalized": 15,
                "policy_lock": "ACTIVE",
                "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            }
        ),
        encoding="utf-8",
    )

    result = build_phase13_research_backtest_baseline_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["rows_analyzed"] == 15
    assert payload["symbols_count"] == 3
    assert all("stale_fallback" not in p for p in payload["input_paths_checked"])
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
PY

cat > "$PROJECT/tests/regression/test_phase11_normalizer_clears_stale_outputs.py" <<'PY'
import csv
from pathlib import Path

from crypto_decision_lab.reports.phase11_offline_source_normalizer_pack import build_phase11_offline_source_normalizer_pack


def test_phase11_normalizer_clears_stale_normalized_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    out = tmp_path / "out"
    stale = out / "normalized" / "stale_fallback.jsonl"
    stale.parent.mkdir(parents=True, exist_ok=True)
    stale.write_text('{"symbol":"BTC-USDT","source":"SAMPLE_FALLBACK_RESEARCH_ONLY"}\n', encoding="utf-8")

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    public_file = inbox / "btc_usdt_binance_public_klines_1h.csv"
    with public_file.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"])
        w.writeheader()
        w.writerow(
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100.5,
                "volume": 1000,
                "symbol": "BTC-USDT",
                "interval": "1h",
                "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
            }
        )

    result = build_phase11_offline_source_normalizer_pack(out, root)
    payload = result["payload"]

    assert payload["rows_normalized"] == 1
    assert not stale.exists()
    normalized_files = list((out / "normalized").glob("*.jsonl"))
    assert len(normalized_files) == 1
    assert "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY" in normalized_files[0].read_text(encoding="utf-8")
PY

echo "[HOTFIX 13A] Running targeted regressions..."
cd "$PROJECT"
pytest -q \
  tests/regression/test_phase13_backtest_excludes_stale_normalized_artifacts.py \
  tests/regression/test_phase11_normalizer_clears_stale_outputs.py

echo "[HOTFIX 13A] Running impacted tests..."
pytest -q \
  tests/unit/test_phase11_offline_source_normalizer_pack.py \
  tests/integration/test_phase11_offline_source_normalizer_pack_cli.py \
  tests/unit/test_phase13_research_backtest_baseline_pack.py \
  tests/integration/test_phase13_research_backtest_baseline_pack_cli.py

echo "[HOTFIX 13A] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 13A] Refreshing normalizer + Phase 13 backtest without refetching..."
cd "$ROOT"
bash "$ROOT/qrds_phase11_offline_source_normalizer_pack.sh"
bash "$ROOT/qrds_phase13_research_backtest_baseline_pack.sh"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase13_research_backtest_baseline_pack/phase13_research_backtest_baseline_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 13A] Phase 13 summary:")
for k in [
    "gate_answer",
    "station",
    "backtest_baseline_ready",
    "public_data_research_ready",
    "certified_public_rows",
    "acceptance_rows_normalized",
    "rows_analyzed",
    "symbols_count",
    "symbols",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_backtest_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")
print("[HOTFIX 13A] Symbol metrics:")
for m in d.get("payload", {}).get("symbol_metrics", []):
    print(f"{m['symbol']}: rows={m['rows']} cum_return={m['cumulative_return']} ann_vol={m['volatility_annualized_24x365']} max_dd={m['max_drawdown']} positive_rate={m['positive_return_rate']}")
PY

echo "[HOTFIX 13A] Archiving hotfix installer if present..."
mkdir -p "$ROOT/scripts/archive/installers"
if [ -f "$ROOT/qrds_hotfix_13A_backtest_public_rows_no_stale_normalized_artifacts.sh" ]; then
  mv "$ROOT/qrds_hotfix_13A_backtest_public_rows_no_stale_normalized_artifacts.sh" "$ROOT/scripts/archive/installers/"
fi

echo "[HOTFIX 13A] Committing changes..."
cd "$ROOT"
git add -A
git commit -m "Fix Phase 13 stale normalized artifact contamination" || true
git push || true

echo "[HOTFIX 13A] Final status:"
git status --short
