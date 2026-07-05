#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -d "$SCRIPT_DIR/crypto_decision_lab" ]; then
  ROOT="$SCRIPT_DIR"
  PROJECT="$ROOT/crypto_decision_lab"
elif [ "$(basename "$SCRIPT_DIR")" = "crypto_decision_lab" ] && [ -d "$SCRIPT_DIR/src" ]; then
  PROJECT="$SCRIPT_DIR"
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
else
  ROOT="$SCRIPT_DIR"
  PROJECT="$ROOT/crypto_decision_lab"
fi

OUTPUT_DIR="$PROJECT/artifacts/dashboard_portal/portal"
PORT=""
BIND_HOST="0.0.0.0"
BUILD_PORTAL="1"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir|--out|--portal-dir)
      OUTPUT_DIR="${2:?missing value for $1}"
      shift 2
      ;;
    --port)
      PORT="${2:?missing value for --port}"
      shift 2
      ;;
    --bind|--host)
      BIND_HOST="${2:?missing value for $1}"
      shift 2
      ;;
    --no-build|--skip-build)
      BUILD_PORTAL="0"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Usage: bash qrds_portal_serve.sh [--output-dir DIR] [--port PORT] [--bind HOST] [--no-build]

Starts a local static HTTP server for the QRDS research portal.
Creates dashboard_serve_plan.json in the served directory.
If DIR does not contain an index.html, a small safe placeholder is created.
EOF
      exit 0
      ;;
    --*)
      echo "[QRDS PORTAL SERVE] Ignoring unsupported compatibility option: $1" >&2
      if [[ $# -ge 2 && "${2:-}" != --* ]]; then
        shift 2
      else
        shift
      fi
      ;;
    *)
      echo "[QRDS PORTAL SERVE] Ignoring positional compatibility argument: $1" >&2
      shift
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR"

if [ "$BUILD_PORTAL" = "1" ]; then
  if [ -x "$ROOT/qrds_portal_build.sh" ]; then
    bash "$ROOT/qrds_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$ROOT/qrds_dashboard_portal_build.sh" ]; then
    bash "$ROOT/qrds_dashboard_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$PROJECT/qrds_portal_build.sh" ]; then
    bash "$PROJECT/qrds_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  elif [ -x "$PROJECT/qrds_dashboard_portal_build.sh" ]; then
    bash "$PROJECT/qrds_dashboard_portal_build.sh" --output-dir "$OUTPUT_DIR" || true
  fi
fi

if [ ! -f "$OUTPUT_DIR/index.html" ]; then
  cat > "$OUTPUT_DIR/index.html" <<'EOF'
<!doctype html>
<html>
<head><meta charset="utf-8"><title>QRDS Research Portal</title></head>
<body>
<h1>QRDS/QOS Research Portal</h1>
<p>Research-only static portal server is running.</p>
<p>No trading signals, recommendations, allocations, or operational decisions.</p>
</body>
</html>
EOF
fi

if [ -z "$PORT" ]; then
  PORT="$(python - <<'PY'
import socket
for port in range(8150, 8200):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
        except OSError:
            continue
        print(port)
        break
else:
    raise SystemExit("NO_FREE_PORT")
PY
)"
fi

python - "$OUTPUT_DIR" "$PORT" "$BIND_HOST" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

out = Path(sys.argv[1])
port = int(sys.argv[2])
bind_host = sys.argv[3]
plan = {
    "schema": "qrds.dashboard_portal_serve_plan.v1",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "serve_directory": str(out),
    "host": bind_host,
    "bind_host": bind_host,
    "port": port,
    "url": f"http://127.0.0.1:{port}/",
    "codespaces_instruction": f"Ports -> {port} -> Open in Browser / Open Preview",
    "entrypoint": "index.html",
    "index_path": str(out / "index.html"),
    "research_only": True,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}
(out / "dashboard_serve_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
PY

echo "[QRDS PORTAL SERVE] Directory: $OUTPUT_DIR"
echo "[QRDS PORTAL SERVE] Plan: $OUTPUT_DIR/dashboard_serve_plan.json"
echo "[QRDS PORTAL SERVE] Bind: $BIND_HOST"
echo "[QRDS PORTAL SERVE] Port: $PORT"
echo
echo "Codespaces:"
echo "  Ports -> $PORT -> Open in Browser / Open Preview"
echo
echo "Stop server with Ctrl+C."

cd "$OUTPUT_DIR"
exec python -m http.server "$PORT" --bind "$BIND_HOST"
