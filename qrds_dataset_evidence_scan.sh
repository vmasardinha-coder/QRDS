#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/crypto_decision_lab"
PYTHONPATH="src${PYTHONPATH:+:$PYTHONPATH}" python -m crypto_decision_lab.cli.dataset_evidence_scanner "$@"
