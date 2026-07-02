#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "[QRDS 9H] Refreshing available stack/data gates before Data Readiness Matrix..."
if [[ -x "./qrds_evidence_stack.sh" ]]; then
  bash ./qrds_evidence_stack.sh --output-dir artifacts/evidence_stack --symbols BTC-USDT,ETH-USDT,SOL-USDT >/dev/null || true
fi

REPORTS="$(python - <<'PY'
from pathlib import Path
root = Path.cwd()
base = root / "crypto_decision_lab" / "artifacts"
patterns = [
    "evidence_stack/evidence_quality/*.json",
    "evidence_stack/evidence_drilldown/*.json",
    "evidence_stack/evidence_timeline/*.json",
    "evidence_stack/research_promotion/*.json",
    "evidence_stack/human_review/*.json",
    "evidence_stack/oos_validation/*.json",
    "evidence_stack/paper_trading/*.json",
    "evidence_stack/risk_model/*.json",
    "operational_security/*.json",
    "data_coverage/*.json",
    "data_quality/*.json",
    "data_audit/*.json",
    "dataset_manifest/*.json",
    "data_profile/*.json",
]
selected = []
seen = set()
for pattern in patterns:
    matches = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    for p in matches:
        if p.name.endswith("_index.json"):
            continue
        s = str(p)
        if s not in seen:
            selected.append(s)
            seen.add(s)
            break
print(",".join(selected))
PY
)"

echo "[QRDS 9H] Explicit reports found: $REPORTS"
bash qrds_data_readiness_serve.sh --output-dir artifacts/data_readiness --symbols BTC-USDT,ETH-USDT,SOL-USDT --reports "$REPORTS"
