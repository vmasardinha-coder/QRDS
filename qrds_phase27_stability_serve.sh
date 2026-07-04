#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "$ROOT/qrds_phase27_edge_candidate_stability_anti_overfit_pack_serve.sh" "$@"
