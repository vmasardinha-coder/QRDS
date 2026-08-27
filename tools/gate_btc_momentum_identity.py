#!/usr/bin/env python3
from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

VOLATILE_SOURCE_KEYS = {"member_sha256", "v2a_zip_sha256"}
VOLATILE_TOP_LEVEL_KEYS = {"snapshot_sha256", "scientific_identity_sha256", "identity_scheme"}


def _norm_number(x: Any) -> Any:
    if isinstance(x, bool) or x is None:
        return x
    if isinstance(x, int):
        return x
    if isinstance(x, float):
        if not math.isfinite(x):
            raise ValueError("non-finite numeric value forbidden in Momentum identity")
        return 0.0 if x == 0.0 else x
    return x


def _normalize(value: Any, path: tuple[str, ...] = ()) -> Any:
    value = _norm_number(value)
    if isinstance(value, dict):
        out = {}
        for k in sorted(value):
            if not path and k in VOLATILE_TOP_LEVEL_KEYS:
                continue
            if path == ("source",) and k in VOLATILE_SOURCE_KEYS:
                continue
            out[k] = _normalize(value[k], path + (k,))
        return out
    if isinstance(value, list):
        rows = [_normalize(x, path + ("[]",)) for x in value]
        # Cross-sectional row order is representational. Scientific order is
        # carried explicitly by rank_m1/rank_m2 inside each row.
        if path in (("m1", "rows"), ("m2", "rows")):
            return sorted(rows, key=lambda x: (str(x.get("asset", "")), json.dumps(x, sort_keys=True, separators=(",", ":"))))
        return rows
    return value


def scientific_identity_payload(payload: dict) -> dict:
    """Return the deterministic scientific identity projection.

    Raw archive/member hashes remain in the persisted payload for audit, but are
    excluded from scientific identity because they cover bytes after the cutoff
    and ZIP/container metadata that cannot be causal inputs to a historical
    cutoff. The cutoff-filtered row count/member name, effective universe,
    M1/M2 outputs, ranks, summaries and safety contract remain identity-bearing.
    """
    if not isinstance(payload, dict):
        raise TypeError("Momentum payload must be a dict")
    required = {"schema", "cutoff", "classification", "source", "m1", "m2", "safety"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValueError(f"Momentum payload missing identity fields: {missing}")
    return _normalize(copy.deepcopy(payload))


def canonical_bytes(payload: dict) -> bytes:
    body = scientific_identity_payload(payload)
    return (json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def scientific_sha256(payload: dict) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compare_scientific_identity(existing: dict, candidate: dict) -> tuple[bool, dict]:
    a = scientific_identity_payload(existing)
    b = scientific_identity_payload(candidate)
    if a == b:
        return True, {"status": "IDENTICAL_SCIENTIFIC_IDENTITY", "differences": []}

    diffs: list[dict] = []

    def walk(x: Any, y: Any, path: str = "$") -> None:
        if len(diffs) >= 50:
            return
        if type(x) is not type(y):
            diffs.append({"path": path, "existing": x, "candidate": y, "reason": "TYPE"})
            return
        if isinstance(x, dict):
            for k in sorted(set(x) | set(y)):
                p = f"{path}.{k}"
                if k not in x:
                    diffs.append({"path": p, "existing": "<MISSING>", "candidate": y[k], "reason": "MISSING_EXISTING"})
                elif k not in y:
                    diffs.append({"path": p, "existing": x[k], "candidate": "<MISSING>", "reason": "MISSING_CANDIDATE"})
                else:
                    walk(x[k], y[k], p)
                if len(diffs) >= 50:
                    return
        elif isinstance(x, list):
            if len(x) != len(y):
                diffs.append({"path": path, "existing": len(x), "candidate": len(y), "reason": "LENGTH"})
            for i, (xi, yi) in enumerate(zip(x, y)):
                walk(xi, yi, f"{path}[{i}]")
                if len(diffs) >= 50:
                    return
        elif x != y:
            diffs.append({"path": path, "existing": x, "candidate": y, "reason": "VALUE"})

    walk(a, b)
    return False, {"status": "SCIENTIFIC_IDENTITY_MISMATCH", "differences": diffs}
