#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase20_baseline_metrics_null_models_harness_pack_serve.sh" "$@"
