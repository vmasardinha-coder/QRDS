#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then ROOT="/workspaces/QRDS"; fi
PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
export PYTHONPATH="$SRC:${PYTHONPATH:-}"

echo "[HOTFIX 12S] Patching Phase 10 sample intake discovery: inbox overrides fallback samples..."

python - <<'PY'
from pathlib import Path
import re

path = Path("crypto_decision_lab/src/crypto_decision_lab/reports/phase10_offline_sample_intake_promotion_pack.py")
text = path.read_text(encoding="utf-8")

new_func = (
"def _discover_input_files(root: Path, out: Path) -> list[Path]:\n"
"    # If manual_intake/inbox has CSV/JSONL files, use ONLY inbox files.\n"
"    # If inbox is empty, use artifact sample inputs as fallback.\n"
"    # This prevents public/real inbox data from being contaminated by fallback samples.\n"
"    inbox = root / \"crypto_decision_lab\" / \"manual_intake\" / \"inbox\"\n"
"    inbox_files: list[Path] = []\n"
"    if inbox.exists():\n"
"        inbox_files = sorted([\n"
"            p for p in inbox.glob(\"*\")\n"
"            if p.is_file() and p.suffix.lower() in {\".jsonl\", \".csv\"}\n"
"        ])\n"
"    if inbox_files:\n"
"        return inbox_files\n"
"\n"
"    sample_dir = out / \"sample_inputs\"\n"
"    sample_files: list[Path] = []\n"
"    if sample_dir.exists():\n"
"        sample_files = sorted([\n"
"            p for p in sample_dir.glob(\"*\")\n"
"            if p.is_file() and p.suffix.lower() in {\".jsonl\", \".csv\"}\n"
"        ])\n"
"    return sample_files\n"
)

pattern = r'def _discover_input_files\(root: Path, out: Path\) -> list\[Path\]:\n(?:    .*\n)+?    return files\n'
if not re.search(pattern, text):
    if "If manual_intake/inbox has CSV/JSONL files, use ONLY inbox files" not in text:
        raise SystemExit("Could not find old _discover_input_files function to patch.")
else:
    text = re.sub(pattern, new_func + "\n", text)
    path.write_text(text, encoding="utf-8")
PY

cat > "$PROJECT/tests/regression/test_phase12_public_inbox_excludes_fallback_samples.py" <<'PY'
import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.phase10_offline_sample_intake_promotion_pack import build_phase10_offline_sample_intake_promotion_pack


def test_public_inbox_files_exclude_artifact_fallback_samples(tmp_path: Path) -> None:
    root = tmp_path / "repo"

    prior = root / "crypto_decision_lab" / "artifacts" / "phase10_offline_intake_validation_pack" / "phase10_offline_intake_validation_pack_index.json"
    prior.parent.mkdir(parents=True)
    prior.write_text(
        json.dumps(
            {
                "gate_answer": "PHASE10_OFFLINE_INTAKE_VALIDATION_PACK_READY_RESEARCH_ONLY",
                "payload": {
                    "template_validations": [
                        {"symbol": "BTC-USDT", "interval": "1h", "valid": True, "template_path": "template"}
                    ]
                },
            }
        ),
        encoding="utf-8",
    )

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True)
    public_file = inbox / "btc_usdt_binance_public_klines_1h.csv"
    with public_file.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"],
        )
        w.writeheader()
        for i in range(5):
            w.writerow(
                {
                    "timestamp": f"2026-01-02T0{i}:00:00Z",
                    "open": 100 + i,
                    "high": 101 + i,
                    "low": 99 + i,
                    "close": 100.5 + i,
                    "volume": 1000 + i,
                    "symbol": "BTC-USDT",
                    "interval": "1h",
                    "source": "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY",
                }
            )

    result = build_phase10_offline_sample_intake_promotion_pack(tmp_path / "out", root)
    payload = result["payload"]

    assert payload["files_validated"] == 1
    assert payload["valid_rows"] == 5
    assert payload["staging_rows"] == 5
    assert payload["canonical_data_writes"] == 0
    assert payload["promotion_allowed"] is False
    assert payload["validated_staging_manifest"]["entries"][0]["source_file"].endswith("btc_usdt_binance_public_klines_1h.csv")
PY

echo "[HOTFIX 12S] Running targeted regression..."
cd "$PROJECT"
pytest -q tests/regression/test_phase12_public_inbox_excludes_fallback_samples.py

echo "[HOTFIX 12S] Running impacted tests..."
pytest -q \
  tests/unit/test_phase10_offline_sample_intake_promotion_pack.py \
  tests/integration/test_phase10_offline_sample_intake_promotion_pack_cli.py \
  tests/unit/test_phase12_public_data_research_readiness_certification_pack.py \
  tests/integration/test_phase12_public_data_research_readiness_certification_pack_cli.py

echo "[HOTFIX 12S] Running full suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[HOTFIX 12S] Refreshing public-data pipeline WITHOUT refetching..."
cd "$ROOT"
bash "$ROOT/qrds_phase11_offline_source_normalizer_pack.sh"
bash "$ROOT/qrds_phase10_offline_sample_intake_promotion_pack.sh"
bash "$ROOT/qrds_phase10_sample_quality_promotion_gate_pack.sh"
bash "$ROOT/qrds_phase10_depth_expansion_readiness_pack.sh"
bash "$ROOT/qrds_phase11_canonical_promotion_dry_run_lock_pack.sh"
bash "$ROOT/qrds_phase11_data_drop_acceptance_pipeline_pack.sh"
bash "$ROOT/qrds_phase12_public_data_research_readiness_certification_pack.sh"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))
print("[HOTFIX 12S] Certification summary:")
for k in [
    "gate_answer",
    "station",
    "public_data_research_ready",
    "public_file_count",
    "public_rows_total",
    "acceptance_data_drop_mode",
    "acceptance_rows_normalized",
    "acceptance_valid_rows",
    "acceptance_staging_rows",
    "acceptance_total_gap_rows",
    "quality_sample_quality_ready",
    "quality_full_depth_ready",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_certification_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")

q = Path("crypto_decision_lab/artifacts/phase10_sample_quality_promotion_gate_pack/phase10_sample_quality_promotion_gate_pack_index.json")
if q.exists():
    x = json.loads(q.read_text(encoding="utf-8"))
    print("[HOTFIX 12S] Quality summary:")
    for k in ["sample_quality_ready", "full_depth_ready", "total_staged_rows", "promotion_allowed", "canonical_data_writes"]:
        print(f"{k}: {x.get(k)}")
PY

echo "[HOTFIX 12S] Archiving hotfix installer if present..."
mkdir -p "$ROOT/scripts/archive/installers"
if [ -f "$ROOT/qrds_hotfix_12S_public_only_staging_no_fallback_contamination.sh" ]; then
  mv "$ROOT/qrds_hotfix_12S_public_only_staging_no_fallback_contamination.sh" "$ROOT/scripts/archive/installers/"
fi

echo "[HOTFIX 12S] Committing changes..."
cd "$ROOT"
git add -A
git commit -m "Fix public inbox staging fallback contamination" || true
git push || true

echo "[HOTFIX 12S] Final status:"
git status --short
