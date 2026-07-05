#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${QRDS_ROOT:-$(pwd)}"
if [[ "$(basename "$ROOT")" == "crypto_decision_lab" ]]; then ROOT="$(cd "$ROOT/.." && pwd)"; else ROOT="$(cd "$ROOT" && pwd)"; fi
exec bash "$ROOT/qrds_phase37_export_review_bundle_single_portal_index_serve.sh" "$@"
