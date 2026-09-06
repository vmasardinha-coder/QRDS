#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

SCHEMA = "qrds.factory.invalidated_source_qualification_search.v1"
ORIGINAL_REPO = "wesleyzilva/tradetech"
B3_TICK_ENDPOINTS = (
    "https://arquivos.b3.com.br/apinegocios/tickercsv/{date}",
    "https://arquivos.b3.com.br/rapinegocios/tickercsv/{date}",
)
B3_BDI_ROOT = "https://arquivos.b3.com.br/bdi/"
SAMPLE_DATES = ("2025-01-02", "2025-03-03", "2025-06-02", "2025-09-01", "2025-12-12")
CADENCE_HOURS = 2
GITHUB_PER_QUERY = 30
GITHUB_QUERIES = (
    'filename:WINFUT extension:csv',
    'WINFUT_5min extension:csv',
    'WINFUT_F_0_5min.csv',
    'WIN$N 5min extension:csv',
    'WINFUT timestamp open high low close extension:csv',
    'WINFUT datetime open high low close extension:csv',
    '"mini indice futuro" 5min extension:csv',
    '"mini índice futuro" 5min extension:csv',
    '"WIN B3" OHLC 5min extension:csv',
    '"WINFUT" volume timestamp extension:csv',
    '"mini indice" intraday B3 extension:csv',
    '"WIN continuous" futures Brazil extension:csv',
)
REQUIRED_GATE_BOOLS = (
    "qualified",
    "free_or_official_auditable",
    "publication_semantics_proven",
    "revision_semantics_proven",
    "identity_qa_pass",
    "schema_qa_pass",
    "point_in_time_valid",
    "independent_unseen_evaluation_data",
    "no_historical_backfill_credit",
)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _win_identity_hint(sample: str, path: str | None = None) -> bool:
    text = f"{path or ''}\n{sample}".upper()
    strong = (
        r"\bWINFUT(?:\b|_)", r"\bWIN\$N\b", r"\bWIN[FGHJKMNQUVXZ]\d{2}\b",
        r"MINI[-_ ]?INDICE", r"MINI[-_ ]?ÍNDICE", r"INDICE FUTURO", r"ÍNDICE FUTURO",
        r"B3.{0,80}\bWIN\b", r"BM&F.{0,80}\bWIN\b", r"BVMF-DERIVATIVES.{0,80}\bWIN",
    )
    return any(re.search(pattern, text) for pattern in strong)


def _intraday_schema_hint(sample: str) -> bool:
    text = sample.upper()
    has_time = any(token in text for token in ("TIMESTAMP", "DATETIME", "DATE,TIME", "DATA,HORA", "DATA;HORA", "DATAREFERENCIA", "HORAFECHAMENTO"))
    has_ohlc = all(token in text for token in ("OPEN", "HIGH", "LOW", "CLOSE")) or all(
        token in text for token in ("ABERTURA", "MAXIMA", "MINIMA", "FECHAMENTO")
    ) or all(token in text for token in ("ABERTURA", "MÁXIMA", "MÍNIMA", "FECHAMENTO"))
    has_trade_price = any(token in text for token in ("PRICE", "PRECO", "PREÇO", "PRECONEGOCIO"))
    return has_time and (has_ohlc or has_trade_price) and ("," in text or ";" in text or "\t" in text)


def _candidate_priority(path: str, repo: str) -> int:
    text = f"{path} {repo}".upper()
    score = 0
    if path.lower().endswith((".csv", ".txt", ".parquet")): score += 4
    if "WINFUT" in text or "WIN$N" in text: score += 8
    if re.search(r"\bWIN[FGHJKMNQUVXZ]\d{2}\b", text): score += 7
    if "MINI" in text and ("INDICE" in text or "ÍNDICE" in text): score += 5
    if any(x in text for x in ("5MIN", "5_MIN", "5M", "5-MIN", "INTRADAY")): score += 4
    if any(x in text for x in ("B3", "BMF", "BM&F", "FUTURE", "FUTURO")): score += 2
    return score


def _sample_response(session: requests.Session, url: str) -> dict[str, Any]:
    try:
        # The official rapinegocios endpoint returns HTTP 200 with an empty body when
        # probed with a Range header. Read only the stream prefix without Range so
        # physical payload presence can be measured without downloading the full file.
        with session.get(url, timeout=30, stream=True, allow_redirects=True) as r:
            status = int(r.status_code)
            sample = b""
            if 200 <= status < 400:
                for chunk in r.iter_content(chunk_size=16384):
                    if chunk:
                        sample += chunk
                    if len(sample) >= 65536:
                        break
            text = sample[:65536].decode("latin-1", errors="ignore")
            return {
                "url": url,
                "final_url": str(r.url),
                "http_status": status,
                "reachable": 200 <= status < 400,
                "content_type": r.headers.get("content-type"),
                "content_length": r.headers.get("content-length"),
                "sample_bytes": len(sample),
                "sample_sha256": hashlib.sha256(sample).hexdigest() if sample else None,
                "zip_magic": sample.startswith(b"PK\x03\x04"),
                "win_identity_hint": _win_identity_hint(text, str(r.url)),
                "csv_schema_hint": _intraday_schema_hint(text),
            }
    except Exception as exc:
        return {
            "url": url,
            "reachable": False,
            "error": f"{type(exc).__name__}: {exc}",
            "zip_magic": False,
            "win_identity_hint": False,
            "csv_schema_hint": False,
        }


def _official_b3_probes(session: requests.Session) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for template in B3_TICK_ENDPOINTS:
        for date in SAMPLE_DATES:
            row = _sample_response(session, template.format(date=date))
            row["official_surface"] = "B3_TRADE_BY_TRADE"
            row["probe_date"] = date
            rows.append(row)
    bdi = _sample_response(session, B3_BDI_ROOT)
    bdi["official_surface"] = "B3_BDI"
    rows.append(bdi)
    return rows


def _deficiencies(identity: bool, schema: bool) -> list[str]:
    missing = []
    if not identity: missing.append("IDENTITY_NOT_PROVEN")
    if not schema: missing.append("INTRADAY_SCHEMA_NOT_PROVEN")
    missing += ["PUBLICATION_SEMANTICS_NOT_PROVEN", "REVISION_SEMANTICS_NOT_PROVEN", "PIT_NOT_PROVEN"]
    return missing


def _github_candidates(session: requests.Session, token: str | None) -> list[dict[str, Any]]:
    if not token:
        return [{"status": "SKIPPED_NO_GITHUB_TOKEN"}]
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    discovered: list[dict[str, Any]] = []
    seen: set[str] = set()
    errors: list[dict[str, Any]] = []
    for query in GITHUB_QUERIES:
        try:
            r = session.get("https://api.github.com/search/code", params={"q": query, "per_page": GITHUB_PER_QUERY}, headers=headers, timeout=30)
            r.raise_for_status()
            for item in r.json().get("items", []):
                repo = str((item.get("repository") or {}).get("full_name") or "")
                if not repo or repo.lower() == ORIGINAL_REPO.lower():
                    continue
                key = str(item.get("html_url") or item.get("url") or "")
                if not key or key in seen:
                    continue
                seen.add(key)
                path = str(item.get("path") or "")
                discovered.append({
                    "query": query, "repository": repo, "path": path,
                    "html_url": item.get("html_url"), "api_url": item.get("url"),
                    "priority": _candidate_priority(path, repo),
                })
        except Exception as exc:
            errors.append({"query": query, "status": "SEARCH_ERROR_FAIL_CLOSED", "error": f"{type(exc).__name__}: {exc}"})
    discovered.sort(key=lambda x: (-int(x["priority"]), str(x["repository"]), str(x["path"])))
    out: list[dict[str, Any]] = []
    for item in discovered:
        row: dict[str, Any] = {
            "query": item["query"], "repository": item["repository"], "path": item["path"],
            "html_url": item["html_url"], "search_priority": item["priority"],
            "provenance_class": "INDEPENDENT_PUBLIC_REPOSITORY",
            "independent_of_invalidated_source": True, "free_auditable_candidate": True,
            "identity_qa_pass": False, "schema_qa_pass": False,
            "publication_semantics_proven": False, "revision_semantics_proven": False,
            "point_in_time_valid": False, "status": "DISCOVERED_NOT_QUALIFIED",
        }
        try:
            fr = session.get(str(item["api_url"]), headers=headers, timeout=20)
            fr.raise_for_status()
            obj = fr.json()
            raw = base64.b64decode(obj.get("content", "")) if obj.get("encoding") == "base64" else b""
            sample = raw[:65536].decode("latin-1", errors="ignore")
            row["resource_sha"] = obj.get("sha")
            row["sample_bytes"] = len(raw[:65536])
            row["identity_qa_pass"] = _win_identity_hint(sample, str(item["path"]))
            row["schema_qa_pass"] = _intraday_schema_hint(sample)
            row["deficiencies"] = _deficiencies(bool(row["identity_qa_pass"]), bool(row["schema_qa_pass"]))
            if row["identity_qa_pass"] and row["schema_qa_pass"]:
                row["status"] = "SCHEMA_IDENTITY_CANDIDATE_STILL_PIT_UNQUALIFIED"
            elif not row["identity_qa_pass"]:
                row["status"] = "DISCOVERY_IRRELEVANT_IDENTITY_NOT_PROVEN"
        except Exception as exc:
            row["inspection_error"] = f"{type(exc).__name__}: {exc}"
            row["deficiencies"] = _deficiencies(False, False)
        out.append(row)
    return out + errors


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


def _source_contract(root_cause: dict[str, Any]) -> dict[str, Any]:
    minimum = _find_key(root_cause, "minimum_sessions_required")
    if minimum is None:
        minimum = _find_key(root_cause, "minimum_sessions_required_for_first_causal_z")
    return {
        "instrument": "WIN_B3_MINI_INDEX_FUTURES",
        "bar_interval": "M5",
        "minimum_sessions_required": minimum,
        "identity_must_be_proven": True,
        "timezone_and_session_semantics_must_be_proven": True,
        "publication_semantics_must_be_proven": True,
        "revision_semantics_must_be_proven": True,
        "point_in_time_must_be_proven": True,
        "independent_unseen_evaluation_must_be_proven": True,
        "historical_backfill_credit": 0,
    }


def _mt5_source_evidence(packet_path: Path | None) -> dict[str, Any]:
    if packet_path is None or not packet_path.is_file():
        return {"status": "MT5_PACKET_NOT_AVAILABLE", "source_admission_pass": False, "blocks_other_sources": False}
    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        matches = []
        for record in packet.get("records") or []:
            identity_text = " ".join(str(record.get(k) or "") for k in ("symbol", "description", "path"))
            if _win_identity_hint(identity_text):
                matches.append({
                    "symbol": record.get("symbol"),
                    "description": record.get("description"),
                    "path": record.get("path"),
                    "earliest_observation_utc": record.get("earliest_observation_utc"),
                    "latest_observation_utc": record.get("latest_observation_utc"),
                    "captured_bar_count": int(record.get("captured_bar_count") or len(record.get("bars") or [])),
                })
        return {
            "status": "MT5_WIN_IDENTITY_SURFACE_DISCOVERED_REVIEW_REQUIRED" if matches else "MT5_PACKET_NO_WIN_IDENTITY_MATCH",
            "source_packet_sha256": packet.get("packet_sha256"),
            "source_identity_semantics": packet.get("source_identity_semantics"),
            "matching_record_count": len(matches),
            "matching_records": matches[:20],
            "source_admission_pass": False,
            "prospective_credit": 0,
            "historical_backfill_credit": 0,
            "blocks_other_sources": False,
            "next_requirement": "PROVE_BROKER_SYMBOL_MAPPING_HISTORY_SESSION_TIMEZONE_PUBLICATION_REVISION_AND_PIT_BEFORE_SOURCE_GATE",
        }
    except Exception as exc:
        return {
            "status": "MT5_PACKET_PARSE_ERROR_FAIL_CLOSED",
            "error": f"{type(exc).__name__}: {exc}",
            "source_admission_pass": False,
            "blocks_other_sources": False,
        }


def validate_existing_gate(gate_path: Path, runtime_root: Path) -> dict[str, Any]:
    if not gate_path.exists():
        return {"present": False, "valid": False, "reason": "SOURCE_GATE_ABSENT"}
    try:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        for key in REQUIRED_GATE_BOOLS:
            if gate.get(key) is not True:
                return {"present": True, "valid": False, "reason": f"GATE_BOOL_NOT_TRUE:{key}"}
        if gate.get("economics_pre_read") is not False:
            return {"present": True, "valid": False, "reason": "ECONOMICS_PRE_READ_NOT_FALSE"}
        if not str(gate.get("evaluation_namespace") or "").strip():
            return {"present": True, "valid": False, "reason": "EMPTY_EVALUATION_NAMESPACE"}
        windows = gate.get("windows") or {}
        discovery = windows.get("discovery") or {}
        replication = windows.get("replication") or {}
        if not all(discovery.get(k) for k in ("start", "end")) or not all(replication.get(k) for k in ("start", "end")):
            return {"present": True, "valid": False, "reason": "WINDOWS_INCOMPLETE"}
        if discovery["end"] >= replication["start"]:
            return {"present": True, "valid": False, "reason": "DISCOVERY_REPLICATION_OVERLAP"}
        rel = str(gate.get("dataset_relative_path") or "")
        dataset = runtime_root / rel.removeprefix("runtime/")
        if not dataset.is_file():
            return {"present": True, "valid": False, "reason": "DATASET_MISSING"}
        actual = hashlib.sha256(dataset.read_bytes()).hexdigest()
        if actual != gate.get("dataset_sha256"):
            return {"present": True, "valid": False, "reason": "DATASET_HASH_MISMATCH"}
        return {"present": True, "valid": True, "reason": "STRICT_SOURCE_GATE_GREEN", "dataset_sha256": actual}
    except Exception as exc:
        return {"present": True, "valid": False, "reason": f"GATE_PARSE_ERROR:{type(exc).__name__}:{exc}"}


def search(root_cause: dict[str, Any], gate_path: Path, runtime_root: Path, token: str | None = None,
           session: requests.Session | None = None, mt5_packet_path: Path | None = None) -> dict[str, Any]:
    s = session or requests.Session()
    s.headers.update({"User-Agent": "QRDS-invalidated-source-qualification-search/4.0"})
    gate = validate_existing_gate(gate_path, runtime_root)
    official = _official_b3_probes(s)
    github = _github_candidates(s, token)
    mt5 = _mt5_source_evidence(mt5_packet_path)
    reachable_official = sum(1 for row in official if row.get("reachable"))
    official_payloads = sum(1 for row in official if int(row.get("sample_bytes") or 0) > 0 or row.get("zip_magic") is True)
    promising_free = sum(1 for row in github if str(row.get("status", "")).startswith("SCHEMA_IDENTITY"))
    irrelevant = sum(1 for row in github if str(row.get("status", "")).startswith("DISCOVERY_IRRELEVANT"))
    affected = root_cause.get("affected_scope") or {}
    status = "SOURCE_GATE_GREEN" if gate["valid"] else "ACTIVE_SEARCHING_QUALIFICATION"
    blockers = [] if gate["valid"] else [
        "EXACT_WIN_SOURCE_IDENTITY", "M5_SCHEMA_AND_SESSION_TIMEZONE", "MINIMUM_HISTORY_COVERAGE",
        "PUBLICATION_SEMANTICS", "REVISION_SEMANTICS", "POINT_IN_TIME_VALIDITY",
        "INDEPENDENT_UNSEEN_EVALUATION_WINDOWS", "HASH_BOUND_DATASET",
    ]
    return {
        "schema": SCHEMA,
        "generated_at_utc": utcnow(),
        "status": status,
        "cadence_hours": CADENCE_HOURS,
        "root_cause_classification": root_cause.get("root_cause_classification"),
        "affected_family_count": int(affected.get("family_count") or 0),
        "source_gate": gate,
        "frozen_source_contract": _source_contract(root_cause),
        "blocking_requirements": blockers,
        "search_strategy": {
            "mode": "PROVENANCE_FIRST_NOT_GENERIC_CSV_HUNT",
            "priority_order": ["OFFICIAL_B3_EXACT_SURFACE", "MT5_READ_ONLY_EXACT_WIN_IDENTITY", "INDEPENDENT_PUBLIC_EXACT_WIN_DATASET"],
            "official_b3_tick_endpoint_variants": list(B3_TICK_ENDPOINTS),
            "generic_search_hit_may_green_gate": False,
            "reachability_may_green_gate": False,
            "failed_identity_hits_are_noise_not_data_gap_evidence": True,
        },
        "search": {
            "official_b3_probes": official,
            "mt5_read_only_source_evidence": mt5,
            "independent_free_github_candidates": github,
            "reachable_official_probe_count": reachable_official,
            "official_payload_probe_count": official_payloads,
            "schema_identity_candidate_count": promising_free,
            "irrelevant_identity_candidate_count": irrelevant,
            "github_query_count": len(GITHUB_QUERIES),
            "github_candidate_count": sum(1 for row in github if row.get("repository")),
            "github_per_query": GITHUB_PER_QUERY,
            "original_invalidated_source_excluded_from_independent_candidates": True,
        },
        "qualification_policy": {
            "free_or_official_auditable_required": True,
            "publication_semantics_required": True,
            "revision_semantics_required": True,
            "identity_schema_qa_required": True,
            "point_in_time_required": True,
            "independent_unseen_evaluation_required": True,
            "nonoverlapping_discovery_replication_required": True,
            "dataset_hash_required": True,
            "no_candidate_promoted_by_reachability_alone": True,
            "mt5_identity_discovery_does_not_self_admit": True,
        },
        "definitive_data_gap_allowed": False if not gate["valid"] else None,
        "next_action": "HAND_OFF_TO_REQUALIFICATION" if gate["valid"] else "RESOLVE_BLOCKING_REQUIREMENTS_BY_PROVENANCE_PRIORITY_FAIL_CLOSED",
        "safety": {
            "research_only": True, "shadow_only": True, "not_approved": True,
            "engine_feed": False, "orders": 0, "real_capital": 0,
            "no_retune": True, "no_backfill": True, "no_counter_reset": True,
            "fail_closed": True, "h1_economics_read": False,
            "scientific_change_allowed": False,
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root-cause", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--mt5-packet")
    args = ap.parse_args()
    root = json.loads(Path(args.root_cause).read_text(encoding="utf-8"))
    if root.get("root_cause_classification") != "SOURCE_DATA_GAP":
        raise SystemExit("ROOT_CAUSE_NOT_SOURCE_DATA_GAP")
    out = search(
        root,
        Path(args.gate),
        Path(args.runtime_root),
        token=os.environ.get("GITHUB_TOKEN"),
        mt5_packet_path=Path(args.mt5_packet) if args.mt5_packet else None,
    )
    p = Path(args.output)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": out["status"],
        "affected_family_count": out["affected_family_count"],
        "minimum_sessions_required": out["frozen_source_contract"]["minimum_sessions_required"],
        "source_gate": out["source_gate"]["reason"],
        "blocking_requirements": out["blocking_requirements"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())