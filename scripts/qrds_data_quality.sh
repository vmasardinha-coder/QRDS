#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
exec bash qrds_data_quality.sh "$@"
