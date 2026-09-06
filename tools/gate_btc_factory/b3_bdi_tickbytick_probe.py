#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import requests

HOST = "https://arquivos.b3.com.br"
CLASSIFICATIONS_URL = f"{HOST}/bdi/table/classifications"
TABLE_KEY = "TickByTickDerivatives"
TABLE_CLASSIFICATION = "Derivativos de bolsa"
TABLE_FRIENDLY_NAME = "Negócio a negócio"
PAGE_SIZE = 1000


def _sha(raw: bytes) -> str | None:
    return hashlib.sha256(raw).hexdigest() if raw else None


def _find_table(obj: Any) -> dict[str, Any] | None:
    if isinstance(obj, dict):
        key = str(obj.get("name") or obj.get("tableName") or obj.get("endpoint") or obj.get("key") or "")
        if key == TABLE_KEY:
            return obj
        for value in obj.values():
            found = _find_table(value)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_table(value)
            if found is not None:
                return found
    return None


def _find_key(obj: Any, wanted: str) -> Any:
    if isinstance(obj, dict):
        if wanted in obj:
            return obj[wanted]
        for value in obj.values():
            found = _find_key(value, wanted)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _find_key(value, wanted)
            if found is not None:
                return found
    return None


def probe(session: requests.Session, probe_date: str) -> dict[str, Any]:
    headers = {"User-Agent": "QRDS-B3-BDI-source-qualification/1.0"}
    out: dict[str, Any] = {
        "schema": "qrds.factory.b3_bdi_tickbytick_derivatives_probe.v1",
        "provider": "B3",
        "source_role": "OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED",
        "table_key": TABLE_KEY,
        "expected_classification": TABLE_CLASSIFICATION,
        "expected_friendly_name": TABLE_FRIENDLY_NAME,
        "probe_date": probe_date,
        "source_gate_credit": 0,
        "historical_backfill_credit": 0,
        "economics_read": False,
    }

    try:
        cr = session.get(CLASSIFICATIONS_URL, timeout=30, headers=headers)
        class_raw = cr.content
        class_json = cr.json() if 200 <= cr.status_code < 300 and class_raw else None
        row = _find_table(class_json) if class_json is not None else None
        out["classification_probe"] = {
            "url": CLASSIFICATIONS_URL,
            "method": "GET",
            "http_status": int(cr.status_code),
            "response_bytes": len(class_raw),
            "response_sha256": _sha(class_raw),
            "table_key_found": row is not None,
            "matched_entry": row,
        }
    except Exception as exc:
        out["classification_probe"] = {
            "url": CLASSIFICATIONS_URL,
            "method": "GET",
            "error": f"{type(exc).__name__}: {exc}",
            "table_key_found": False,
        }
        row = None

    table_url = f"{HOST}/bdi/table/{TABLE_KEY}/{probe_date}/{probe_date}/1/{PAGE_SIZE}"
    try:
        tr = session.post(
            table_url,
            data=b"{}",
            headers={**headers, "Content-Type": "application/json"},
            timeout=60,
        )
        raw = tr.content
        obj = tr.json() if 200 <= tr.status_code < 300 and raw else None
        table = obj.get("table") if isinstance(obj, dict) and isinstance(obj.get("table"), dict) else {}
        columns = table.get("columns") if isinstance(table, dict) else None
        values = table.get("values") if isinstance(table, dict) else None
        column_names = []
        if isinstance(columns, list):
            for col in columns:
                if isinstance(col, dict):
                    column_names.append(str(col.get("name") or col.get("label") or ""))
                else:
                    column_names.append(str(col))
        sample_rows = values[:20] if isinstance(values, list) else []
        sample_text = json.dumps(sample_rows, ensure_ascii=False).upper()
        out["table_probe"] = {
            "url": table_url,
            "method": "POST",
            "request_body": {},
            "content_type": "application/json",
            "http_status": int(tr.status_code),
            "response_bytes": len(raw),
            "response_sha256": _sha(raw),
            "json_object": isinstance(obj, dict),
            "column_count": len(column_names),
            "columns": column_names,
            "row_count_page1": len(values) if isinstance(values, list) else None,
            "sample_contains_win_identity": "WIN" in sample_text,
            "limit_date": _find_key(obj, "limitDate") if obj is not None else None,
            "publication_date": _find_key(obj, "publicationDate") if obj is not None else None,
            "republished": _find_key(obj, "republished") if obj is not None else None,
            "errata": _find_key(obj, "errata") if obj is not None else None,
        }
    except Exception as exc:
        out["table_probe"] = {
            "url": table_url,
            "method": "POST",
            "request_body": {},
            "content_type": "application/json",
            "error": f"{type(exc).__name__}: {exc}",
            "response_bytes": 0,
        }

    cp = out["classification_probe"]
    tp = out["table_probe"]
    physical = bool(
        cp.get("table_key_found")
        and 200 <= int(tp.get("http_status") or 0) < 300
        and int(tp.get("response_bytes") or 0) > 0
        and tp.get("json_object") is True
    )
    out["status"] = "BDI_TICK_SURFACE_OBSERVED_NOT_SOURCE_GATE" if physical else "BDI_TICK_SURFACE_NOT_PHYSICALLY_PROVEN"
    out["physical_surface_observed"] = physical
    out["strict_source_gate_green"] = False
    out["blocking_requirements_preserved"] = [
        "EXACT_WIN_SOURCE_IDENTITY",
        "M5_SCHEMA_AND_SESSION_TIMEZONE",
        "MINIMUM_HISTORY_COVERAGE",
        "PUBLICATION_SEMANTICS",
        "REVISION_SEMANTICS",
        "POINT_IN_TIME_VALIDITY",
        "INDEPENDENT_UNSEEN_EVALUATION_WINDOWS",
        "HASH_BOUND_DATASET",
    ]
    out["safety"] = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
        "h1_economics_read": False,
    }
    return out


def default_probe_date() -> str:
    d = date.today()
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", dest="probe_date", default=default_probe_date())
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    s = requests.Session()
    out = probe(s, args.probe_date)
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": out["status"], "date": args.probe_date, "source_gate_green": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
