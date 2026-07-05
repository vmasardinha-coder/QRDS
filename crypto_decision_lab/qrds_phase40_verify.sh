#!/usr/bin/env bash
set -euo pipefail
ROOT_DEFAULT="/workspaces/QRDS"
ROOT="${QRDS_ROOT:-$(pwd)}"
if [[ ! -d "$ROOT/crypto_decision_lab" && -d "$ROOT_DEFAULT/crypto_decision_lab" ]]; then ROOT="$ROOT_DEFAULT"; fi
PROJECT_DIR="$ROOT/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:$PROJECT_DIR:${PYTHONPATH:-}"
python scripts/phase40_portal_visual_qa_accessibility_link_audit.py
python -m pytest tests/unit/test_phase40_portal_visual_qa_accessibility_link_audit.py -q
python -m pytest -q
