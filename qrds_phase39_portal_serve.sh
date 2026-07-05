#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-$(pwd)}"
if [[ ! -d "$ROOT/crypto_decision_lab" && -d "/workspaces/QRDS/crypto_decision_lab" ]]; then ROOT="/workspaces/QRDS"; fi
cd "$ROOT"
PROJECT_DIR="$ROOT/crypto_decision_lab"
GENERATOR="$PROJECT_DIR/scripts/phase39_interpretation_readiness_information_architecture.py"
OUT_DIR="$PROJECT_DIR/artifacts/phase39_interpretation_readiness_information_architecture"
PORT="0"
BIND="127.0.0.1"
HOST_LABEL="localhost"
SKIP_BUILD="0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --output-dir|--out|--portal-dir) OUT_DIR="$2"; shift 2 ;;
    --port) PORT="$2"; shift 2 ;;
    --bind) BIND="$2"; shift 2 ;;
    --host) HOST_LABEL="$2"; shift 2 ;;
    --no-build|--skip-build) SKIP_BUILD="1"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done
if [[ "$SKIP_BUILD" != "1" ]]; then
  python "$GENERATOR" --output-dir "$OUT_DIR"
fi
PORT_SELECTED="$(python - "$PORT" "$BIND" <<'PY_PORT'
import socket, sys
requested=int(sys.argv[1]); bind=sys.argv[2]
if requested > 0:
    print(requested); raise SystemExit
s=socket.socket(); s.bind((bind,0)); print(s.getsockname()[1]); s.close()
PY_PORT
)"
PORTAL_DIR="$OUT_DIR/portal"
mkdir -p "$PORTAL_DIR"
if [[ ! -f "$PORTAL_DIR/index.html" ]]; then
  cat > "$PORTAL_DIR/index.html" <<'HTML_PLACEHOLDER'
<!doctype html><meta charset="utf-8"><title>QRDS Phase 39</title><h1>QRDS Phase 39 portal placeholder</h1><p>Run without --skip-build to generate the portal.</p>
HTML_PLACEHOLDER
fi
cat > "$OUT_DIR/dashboard_serve_plan.json" <<PLAN_JSON
{
  "phase": 39,
  "app_mode": "INTERACTIVE_RESEARCH_ONLY",
  "policy_lock": "ACTIVE",
  "operational_status": "BLOCKED_RESEARCH_ONLY",
  "edge_validated": false,
  "shadow_decision_allowed": false,
  "decision_layer_allowed": false,
  "trading_signal_generated": false,
  "recommendation_generated": false,
  "allocation_generated": false,
  "canonical_data_writes": 0,
  "bind": "$BIND",
  "host": "$HOST_LABEL",
  "port": $PORT_SELECTED,
  "portal_dir": "$PORTAL_DIR",
  "url": "http://$HOST_LABEL:$PORT_SELECTED/"
}
PLAN_JSON
echo "[QRDS][Phase39] Portal dir: $PORTAL_DIR"
echo "[QRDS][Phase39] Serving at: http://$HOST_LABEL:$PORT_SELECTED/"
echo "[QRDS][Phase39] Codespaces: abra a aba Ports, torne a porta $PORT_SELECTED pública/visível se necessário, e clique no link encaminhado."
cd "$PORTAL_DIR"
python -m http.server "$PORT_SELECTED" --bind "$BIND"
