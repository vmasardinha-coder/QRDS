#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase32_risk_regime_dashboard_navigation_hardening_pack}"
python -m crypto_decision_lab.cli.phase32_risk_regime_dashboard_navigation_hardening_pack --output-dir "$OUT" --repo-root "$ROOT"
