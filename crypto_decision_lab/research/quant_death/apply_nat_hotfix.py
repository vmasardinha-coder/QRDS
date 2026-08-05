from __future__ import annotations

import sys
from pathlib import Path

OLD = '''def serialize_dates(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in obj.items():
        if isinstance(v, (pd.Timestamp, datetime, date)):
            out[k] = pd.Timestamp(v).strftime("%Y-%m-%d")
        elif isinstance(v, np.generic):
            out[k] = v.item()
        elif pd.isna(v) if not isinstance(v, (list, dict, tuple, set)) else False:
            out[k] = ""
        else:
            out[k] = v
    return out
'''

NEW = '''def serialize_dates(obj: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    containers = (list, dict, tuple, set)
    for k, v in obj.items():
        if v is None:
            out[k] = ""
            continue
        if not isinstance(v, containers):
            try:
                if bool(pd.isna(v)):
                    out[k] = ""
                    continue
            except (TypeError, ValueError):
                pass
        if isinstance(v, (pd.Timestamp, datetime, date)):
            out[k] = pd.Timestamp(v).strftime("%Y-%m-%d")
        elif isinstance(v, np.generic):
            out[k] = v.item()
        else:
            out[k] = v
    return out
'''


def main() -> int:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "collect_multisource.py")
    text = target.read_text(encoding="utf-8")
    if NEW in text:
        print(f"NAT_HOTFIX_ALREADY_APPLIED={target}")
        return 0
    count = text.count(OLD)
    if count != 1:
        raise SystemExit(f"FAIL_CLOSED: expected exactly one frozen serialize_dates block, found {count}")
    target.write_text(text.replace(OLD, NEW), encoding="utf-8")
    print(f"NAT_HOTFIX_APPLIED={target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
