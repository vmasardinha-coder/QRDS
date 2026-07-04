#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack}"
python -m crypto_decision_lab.cli.phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack --output-dir "$OUT" --repo-root "$ROOT"
