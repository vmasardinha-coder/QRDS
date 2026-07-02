#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
if [ ! -d "$ROOT/crypto_decision_lab" ]; then ROOT="$(pwd)"; fi
cd "$ROOT/crypto_decision_lab"
python -m crypto_decision_lab.cli.workspace_portal_docs_inventory \
  --output-dir artifacts/workspace_portal_docs_inventory \
  --repo-root "$ROOT"
