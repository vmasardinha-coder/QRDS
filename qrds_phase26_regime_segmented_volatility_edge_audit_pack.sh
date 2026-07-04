#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase26_regime_segmented_volatility_edge_audit_pack}"
python -m crypto_decision_lab.cli.phase26_regime_segmented_volatility_edge_audit_pack --output-dir "$OUT" --repo-root "$ROOT"
