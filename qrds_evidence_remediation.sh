#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$LAB_DIR"
export PYTHONPATH="$LAB_DIR/src:${PYTHONPATH:-}"

python -m crypto_decision_lab.cli.evidence_remediation "$@"
