#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase10_offline_sample_intake_promotion_pack_serve.sh" "$@"
