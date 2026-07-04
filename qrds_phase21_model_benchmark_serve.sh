#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase21_baseline_audit_interpretable_model_benchmark_pack_serve.sh" "$@"
