#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${QRDS_ROOT:-$(pwd)}"
if [[ "$(basename "$ROOT")" == "crypto_decision_lab" ]]; then ROOT="$(cd "$ROOT/.." && pwd)"; else ROOT="$(cd "$ROOT" && pwd)"; fi
exec bash "$ROOT/qrds_phase38_modern_research_portal_layout_ux_polish_serve.sh" "$@"
