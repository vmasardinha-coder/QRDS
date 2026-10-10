"""Resolve reporting authorities without touching any scientific ledger."""
import json
import re
from pathlib import Path


def active_status_path(ledger_root: Path, filename: str = "STATUS.json") -> Path:
    pointer = ledger_root / "ACTIVE_EPOCH.json"
    if not pointer.is_file():
        return ledger_root / filename
    obj = json.loads(pointer.read_text(encoding="utf-8-sig"))
    relative = obj.get("relative_path")
    if not isinstance(relative, str) or not re.fullmatch(r"epochs/[A-Za-z0-9_-]+", relative):
        raise ValueError("INVALID_REPORTING_ACTIVE_EPOCH_PATH")
    target = ledger_root / relative / filename
    if not target.resolve().is_relative_to(ledger_root.resolve()):
        raise ValueError("REPORTING_ACTIVE_EPOCH_ESCAPES_LEDGER")
    # Once an epoch is selected, missing evidence must never fall back to legacy.
    return target
