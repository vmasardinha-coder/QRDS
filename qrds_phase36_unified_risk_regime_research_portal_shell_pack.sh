#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase36_unified_risk_regime_research_portal_shell_pack}"
python -m crypto_decision_lab.cli.phase36_unified_risk_regime_research_portal_shell_pack --output-dir "$OUT" --repo-root "$ROOT"
