#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="$ROOT/crypto_decision_lab"
export PYTHONPATH="$PROJECT/src:${PYTHONPATH:-}"
OUT="${1:-$PROJECT/artifacts/phase17_consensus_quality_drift_monitor_pack}"
python -m crypto_decision_lab.cli.phase17_consensus_quality_drift_monitor_pack --output-dir "$OUT" --repo-root "$ROOT"
