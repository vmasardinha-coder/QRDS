#!/usr/bin/env bash
set -euo pipefail
ROOT="${QRDS_ROOT:-/workspaces/QRDS}"
PROJ="$ROOT/crypto_decision_lab"
cd "$PROJ"
export PYTHONPATH="$PROJ/src:${PYTHONPATH:-}"

PAYLOAD="${1:-}"
if [[ -n "$PAYLOAD" && -f "$PAYLOAD" ]]; then
  python - "$PAYLOAD" <<'PY'
import json, sys
from pathlib import Path
from crypto_decision_lab.scripts.phase66_unified_local_preflight_cli_research_only import unified_preflight
payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
result = unified_preflight(payload)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["preflight_passed"] else 1)
PY
else
  python - <<'PY'
import json
from crypto_decision_lab.scripts.phase66_unified_local_preflight_cli_research_only import SAMPLE_PREFLIGHT_PAYLOAD, unified_preflight
result = unified_preflight(SAMPLE_PREFLIGHT_PAYLOAD)
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["preflight_passed"] else 1)
PY
fi
