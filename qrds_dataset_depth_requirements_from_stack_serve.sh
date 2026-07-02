#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
OUTPUT_DIR="artifacts/dataset_depth_requirements"

# Refresh upstream dataset evidence if wrappers are installed. Non-serve wrappers only.
if [ -x "./qrds_dataset_evidence_scan.sh" ]; then
  echo "[QRDS 9M] Refreshing dataset evidence scan..."
  bash qrds_dataset_evidence_scan.sh --output-dir artifacts/dataset_evidence_scan --symbols "$SYMBOLS" >/dev/null || true
fi
if [ -x "./qrds_dataset_evidence_explorer.sh" ]; then
  echo "[QRDS 9M] Refreshing dataset evidence explorer..."
  bash qrds_dataset_evidence_explorer.sh --output-dir artifacts/dataset_evidence_explorer --symbols "$SYMBOLS" >/dev/null || true
fi
if [ -x "./qrds_dataset_manifest_from_stack_serve.sh" ]; then
  : # Do not call serve/blocking wrappers here.
fi

mapfile -t REPORT_PATHS < <(python - <<'PY'
from pathlib import Path
root = Path.cwd()
patterns = [
    "crypto_decision_lab/artifacts/dataset_evidence_scan/*.json",
    "crypto_decision_lab/artifacts/dataset_evidence_explorer/*.json",
    "crypto_decision_lab/artifacts/dataset_manifest/*.json",
    "crypto_decision_lab/artifacts/data_profile/*.json",
    "crypto_decision_lab/artifacts/data_readiness/*.json",
    "crypto_decision_lab/artifacts/data_gap_remediation/*.json",
    "crypto_decision_lab/artifacts/data_coverage/*.json",
    "crypto_decision_lab/artifacts/data_quality/*.json",
    "crypto_decision_lab/artifacts/data_audit/*.json",
]
seen = set()
for pattern in patterns:
    for p in sorted(root.glob(pattern)):
        if not p.is_file() or p.name.endswith("_index.json"):
            continue
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        print(key)
PY
)
REPORTS="$(IFS=,; echo "${REPORT_PATHS[*]:-}")"
echo "[QRDS 9M] Explicit reports found: ${REPORTS:-NONE}"

bash qrds_dataset_depth_requirements_serve.sh \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --reports "$REPORTS"
