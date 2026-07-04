#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

cd "$ROOT"
mkdir -p scripts/archive/installers

echo "[CLEANUP 13A] Moving root hotfix installers to archive if present..."

for f in \
  "qrds_hotfix_13A_backtest_public_rows_no_stale_normalized_artifacts.sh" \
  "qrds_hotfix_13A_v2_backtest_public_rows_no_stale_normalized_artifacts.sh" \
  "qrds_hotfix_13A_v2_backtest_public_rows_no_stale_normalized_artifacts (1).sh"
do
  if [ -f "$f" ]; then
    mv "$f" "scripts/archive/installers/$f"
    echo "[CLEANUP 13A] Archived $f"
  fi
done

echo "[CLEANUP 13A] Checking root hotfix installers..."
ROOT_LEFT="$(find . -maxdepth 1 -type f -name 'qrds_hotfix_13A*' -print | wc -l | tr -d ' ')"
echo "root_hotfix_installers_left: $ROOT_LEFT"

if [ "$ROOT_LEFT" != "0" ]; then
  echo "[CLEANUP 13A] ERROR: root hotfix installers still present."
  find . -maxdepth 1 -type f -name 'qrds_hotfix_13A*' -print
  exit 1
fi

echo "[CLEANUP 13A] Running focused sanity checks..."
cd "$ROOT/crypto_decision_lab"
pytest -q \
  tests/regression/test_phase11_normalizer_clears_stale_outputs.py \
  tests/regression/test_phase13_backtest_excludes_stale_normalized_artifacts.py \
  tests/unit/test_phase13_research_backtest_baseline_pack.py \
  tests/integration/test_phase13_research_backtest_baseline_pack_cli.py

cd "$ROOT"
echo "[CLEANUP 13A] Committing cleanup..."
git add -A
git commit -m "Archive Phase 13A root hotfix installers" || true
git push || true

echo "[CLEANUP 13A] Final status:"
git status --short
