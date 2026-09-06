#!/usr/bin/env python3
"""Evidence-only full ZIP inspector for the official B3 type=2 intraday surface.

Downloads one recent official response completely, hashes the exact ZIP bytes, and
inspects member names/content for an auditable WIN identity signal and a tabular
trade schema.  It never admits the source, never creates SOURCE_GATE, and never
reads economics.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import requests

SCHEMA = "qrds.factory.b3_derivatives_type2_full_zip_inspector.v1"
URL = "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}?type=2"
WIN_RE = re.compile(r"(?:^|[;,\t\s\"])(WIN[FGHJKMNQUVXZ]\d{2})(?:[;,\t\s\"]|$)", re.IGNORECASE)
MAX_MATCHES = 100


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inspect_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> dict[str, Any]:
    h = hashlib.sha256()
    first_lines: list[str] = []
    win_symbols: set[str] = set()
    bytes_read = 0
    with zf.open(info, "r") as raw:
        wrapper = io.TextIOWrapper(raw, encoding="latin-1", errors="replace", newline="")
        for line_no, line in enumerate(wrapper, start=1):
            encoded = line.encode("latin-1", errors="replace")
            h.update(encoded)
            bytes_read += len(encoded)
            if len(first_lines) < 5:
                first_lines.append(line.rstrip("\r\n")[:2000])
            for match in WIN_RE.finditer(line):
                if len(win_symbols) < MAX_MATCHES:
                    win_symbols.add(match.group(1).upper())
        # TextIOWrapper consumes member to EOF, so digest covers the decoded/re-encoded
        # latin-1 byte stream exactly for these B3 text payloads.
    header = first_lines[0] if first_lines else ""
    delimiter = ";" if header.count(";") >= max(header.count(","), header.count("\t")) else ("," if header.count(",") >= header.count("\t") else "\t")
    columns = next(csv.reader([header], delimiter=delimiter), []) if header else []
    return {
        "name": info.filename,
        "compressed_size": info.compress_size,
        "uncompressed_size": info.file_size,
        "content_sha256_latin1_roundtrip": h.hexdigest(),
        "bytes_scanned": bytes_read,
        "first_lines": first_lines,
        "detected_delimiter": delimiter,
        "columns": columns,
        "win_symbols": sorted(win_symbols),
        "win_identity_observed": bool(win_symbols),
    }


def inspect(session: requests.Session, probe_date: str) -> dict[str, Any]:
    url = URL.format(date=probe_date)
    safety = {
        "research_only": True, "shadow_only": True, "not_approved": True,
        "engine_feed": False, "orders": 0, "real_capital": 0,
        "no_retune": True, "no_backfill": True, "no_counter_reset": True,
        "fail_closed": True, "h1_economics_read": False,
    }
    out: dict[str, Any] = {
        "schema": SCHEMA, "provider": "B3", "probe_date": probe_date,
        "url": url, "source_role": "OFFICIAL_PRIMARY_CANDIDATE_NOT_ADMITTED",
        "strict_source_gate_green": False, "source_gate_credit": 0,
        "historical_backfill_credit": 0, "prospective_credit": 0,
        "economics_read": False, "safety": safety,
        "full_161_session_coverage_proven": False,
        "publication_semantics_proven": False,
        "revision_semantics_proven": False,
        "point_in_time_valid": False,
        "independent_unseen_evaluation_data": False,
    }
    try:
        with tempfile.TemporaryDirectory() as td:
            zip_path = Path(td) / "source.zip"
            with session.get(url, timeout=180, stream=True, allow_redirects=True) as response:
                out["http_status"] = int(response.status_code)
                out["content_disposition"] = response.headers.get("content-disposition")
                out["content_type"] = response.headers.get("content-type")
                if response.status_code != 200:
                    out["status"] = "FULL_ZIP_HTTP_FAIL_CLOSED"
                    return out
                with zip_path.open("wb") as fh:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            fh.write(chunk)
            out["zip_size_bytes"] = zip_path.stat().st_size
            out["zip_sha256"] = sha256_path(zip_path)
            if not zipfile.is_zipfile(zip_path):
                out["status"] = "FULL_RESPONSE_NOT_ZIP_FAIL_CLOSED"
                return out
            with zipfile.ZipFile(zip_path) as zf:
                infos = [i for i in zf.infolist() if not i.is_dir()]
                out["member_count"] = len(infos)
                out["members"] = [_inspect_member(zf, info) for info in infos]
            symbols = sorted({s for m in out["members"] for s in m["win_symbols"]})
            out["win_symbols"] = symbols
            out["exact_win_identity_observed_in_payload"] = bool(symbols)
            out["schema_surface_observed"] = any(len(m.get("columns") or []) >= 4 for m in out["members"])
            out["status"] = (
                "WIN_IDENTITY_PHYSICALLY_OBSERVED_NEEDS_SEMANTIC_QUALIFICATION"
                if symbols else "TYPE2_ZIP_HAS_NO_WIN_IDENTITY_FAIL_CLOSED"
            )
            out["next_requirement"] = (
                "PROVE_SCHEMA_TIMEZONE_PUBLICATION_REVISION_PIT_AND_161_SESSION_COVERAGE_WITHOUT_BACKFILL_CREDIT"
                if symbols else "DO_NOT_ADMIT_TYPE2_AS_WIN_SOURCE_CONTINUE_OFFICIAL_TRANSPORT_DISCOVERY"
            )
    except Exception as exc:
        out["status"] = "FULL_ZIP_INSPECTION_ERROR_FAIL_CLOSED"
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    result = inspect(requests.Session(), args.date)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result.get("status"), "strict_source_gate_green": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
