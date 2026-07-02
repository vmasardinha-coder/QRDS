#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAB="$ROOT/crypto_decision_lab"

OUTPUT_DIR="artifacts/acceptance_runner"
SYMBOLS="BTC-USDT,ETH-USDT,SOL-USDT"
SKIP_PYTEST=0
SKIP_REFRESH=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir)
      OUTPUT_DIR="$2"; shift 2 ;;
    --symbols)
      SYMBOLS="$2"; shift 2 ;;
    --skip-pytest)
      SKIP_PYTEST=1; shift ;;
    --skip-refresh)
      SKIP_REFRESH=1; shift ;;
    *)
      echo "[QRDS 9F] Unknown argument: $1" >&2
      exit 2 ;;
  esac
done

cd "$ROOT"
echo "[QRDS 9F] Acceptance Runner starting..."
echo "[QRDS 9F] Repo: $ROOT"

find "$ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$ROOT/.pytest_cache" "$LAB/.pytest_cache"

REFRESH_STATUS="SKIPPED"
if [[ "$SKIP_REFRESH" -eq 0 && -x "$ROOT/qrds_evidence_stack.sh" ]]; then
  echo "[QRDS 9F] Refreshing evidence stack..."
  set +e
  bash "$ROOT/qrds_evidence_stack.sh" --output-dir artifacts/evidence_stack --symbols "$SYMBOLS"
  REFRESH_RC=$?
  set -e
  if [[ "$REFRESH_RC" -eq 0 ]]; then
    REFRESH_STATUS="PASS"
  else
    REFRESH_STATUS="FAIL"
  fi
else
  echo "[QRDS 9F] Evidence stack refresh skipped or wrapper not installed."
fi

PYTEST_STATUS="SKIPPED"
if [[ "$SKIP_PYTEST" -eq 0 ]]; then
  echo "[QRDS 9F] Running full pytest suite..."
  set +e
  (
    cd "$LAB" && \
    PYTHONPATH="$LAB/src:${PYTHONPATH:-}" \
    pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs
  )
  PYTEST_RC=$?
  set -e
  if [[ "$PYTEST_RC" -eq 0 ]]; then
    PYTEST_STATUS="PASS"
  else
    PYTEST_STATUS="FAIL"
  fi
else
  echo "[QRDS 9F] Pytest skipped by flag."
fi

mkdir -p "$LAB/$OUTPUT_DIR"
git status --short > "$LAB/$OUTPUT_DIR/git_status.txt" || true

cd "$LAB"
PYTHONPATH="$LAB/src:${PYTHONPATH:-}" python -m crypto_decision_lab.cli.acceptance_runner \
  --output-dir "$OUTPUT_DIR" \
  --symbols "$SYMBOLS" \
  --pytest-status "$PYTEST_STATUS" \
  --refresh-status "$REFRESH_STATUS" \
  --git-status-file "$OUTPUT_DIR/git_status.txt"

echo
echo "[QRDS 9F] Acceptance Runner generated: $LAB/$OUTPUT_DIR/index.html"
echo "[QRDS 9F] Pytest status: $PYTEST_STATUS"
echo "[QRDS 9F] Refresh status: $REFRESH_STATUS"
echo "[QRDS 9F] Scope: research validation only; no operational unlock."
