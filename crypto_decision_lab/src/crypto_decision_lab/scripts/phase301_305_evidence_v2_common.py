from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import statistics
import urllib.error
import urllib.parse
import urllib.request
from bisect import bisect_right
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[3]

LOCKS: dict[str, Any] = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "forward_shadow_eligible": False,
    "forward_shadow_started": False,
    "paper_trading_started": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "private_api_allowed": False,
    "account_connection_allowed": False,
    "orders_allowed": False,
    "capital_allowed": False,
    "capital_used": 0,
    "real_orders_created": 0,
    "position_size": 0,
    "canonical_data_writes": 0,
}

REQUIRED_PORTAL_HEADINGS = (
    "O QUE FOI COLETADO",
    "O QUE FOI TESTADO",
    "QUAL ERA A PERGUNTA",
    "O QUE O RESULTADO SIGNIFICA",
    "EXEMPLO COM R$10.000",
    "POR QUE FOI REPROVADO OU APROVADO",
    "O QUE O TESTE NAO PROVA",
    "CONCLUSAO PRATICA",
)

OFFICIAL_ENDPOINT_REGISTRY: dict[str, dict[str, Any]] = {
    "binance_candles": {
        "provider": "BINANCE",
        "market": "USDS_M_FUTURES",
        "endpoint": "https://fapi.binance.com/fapi/v1/klines",
        "docs": (
            "https://developers.binance.com/docs/derivatives/"
            "usds-margined-futures/market-data/rest-api/"
            "Kline-Candlestick-Data"
        ),
        "auth_required": False,
        "method": "GET",
        "max_limit": 1500,
    },
    "binance_funding": {
        "provider": "BINANCE",
        "market": "USDS_M_FUTURES",
        "endpoint": "https://fapi.binance.com/fapi/v1/fundingRate",
        "docs": (
            "https://developers.binance.com/docs/derivatives/"
            "usds-margined-futures/market-data/rest-api/"
            "Get-Funding-Rate-History"
        ),
        "auth_required": False,
        "method": "GET",
        "max_limit": 1000,
    },
    "okx_candles": {
        "provider": "OKX",
        "market": "SWAP",
        "endpoint": "https://www.okx.com/api/v5/market/history-candles",
        "docs": "https://www.okx.com/docs-v5/en/#rest-api-market-data-get-candlesticks-history",
        "auth_required": False,
        "method": "GET",
        "max_limit": 100,
    },
    "bybit_candles": {
        "provider": "BYBIT",
        "market": "LINEAR_PERPETUAL",
        "endpoint": "https://api.bybit.com/v5/market/kline",
        "docs": "https://bybit-exchange.github.io/docs/v5/market/kline",
        "auth_required": False,
        "method": "GET",
        "max_limit": 1000,
    },
    "bybit_funding": {
        "provider": "BYBIT",
        "market": "LINEAR_PERPETUAL",
        "endpoint": "https://api.bybit.com/v5/market/funding/history",
        "docs": "https://bybit-exchange.github.io/docs/v5/market/history-fund-rate",
        "auth_required": False,
        "method": "GET",
        "max_limit": 200,
    },
    "bybit_open_interest": {
        "provider": "BYBIT",
        "market": "LINEAR_PERPETUAL",
        "endpoint": "https://api.bybit.com/v5/market/open-interest",
        "docs": "https://bybit-exchange.github.io/docs/v5/market/open-interest",
        "auth_required": False,
        "method": "GET",
        "max_limit": 200,
    },
    "coinbase_candles": {
        "provider": "COINBASE",
        "market": "SPOT",
        "endpoint": "https://api.exchange.coinbase.com/products/BTC-USD/candles",
        "docs": (
            "https://docs.cdp.coinbase.com/api-reference/"
            "exchange-api/rest-api/products/get-product-candles"
        ),
        "auth_required": False,
        "method": "GET",
        "max_points_per_request": 300,
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def iso_from_ms(value: int) -> str:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def floor_closed_hour_ms(now_ms: int | None = None) -> int:
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    hour = 60 * 60 * 1000
    return (now_ms // hour) * hour - hour


def stable_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")


def fingerprint(payload: Any) -> str:
    return hashlib.sha256(stable_json_bytes(payload)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return path


def write_csv_gz(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def read_csv_gz(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_locks(locks: dict[str, Any]) -> None:
    required_false = (
        "edge_validated",
        "edge_operationally_validated",
        "forward_shadow_eligible",
        "forward_shadow_started",
        "paper_trading_started",
        "decision_layer_allowed",
        "trading_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "operational_decision_allowed",
        "safe_apply_allowed",
        "promotion_allowed",
        "private_api_allowed",
        "account_connection_allowed",
        "orders_allowed",
        "capital_allowed",
    )
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["action_status"] == "NO_ACTION_RESEARCH_ONLY"
    for key in required_false:
        assert locks[key] is False, key
    assert locks["capital_used"] == 0
    assert locks["real_orders_created"] == 0
    assert locks["position_size"] == 0
    assert locks["canonical_data_writes"] == 0


def base_payload(phase: int, status: str) -> dict[str, Any]:
    validate_locks(LOCKS)
    return {
        "phase": phase,
        "project": "QRDS/QOS/GATE BTC",
        "created_at_utc": utc_now_iso(),
        "status": status,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "historical_result_authorizes_execution": False,
        "locks": dict(LOCKS),
    }


def http_get_json(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout_seconds: int = 30,
    attempts: int = 4,
    user_agent: str = "QRDS-Research-Only/301-305",
) -> Any:
    if params:
        query = urllib.parse.urlencode(
            {key: value for key, value in params.items() if value is not None}
        )
        url = f"{url}?{query}"
    request = urllib.request.Request(
        url,
        method="GET",
        headers={
            "Accept": "application/json",
            "User-Agent": user_agent,
        },
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read()
            return json.loads(body.decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == attempts:
                break
            import time
            time.sleep(min(2 ** (attempt - 1), 8))
    raise RuntimeError(f"Public HTTP GET failed after {attempts} attempts: {url}: {last_error}")


def deduplicate_by_timestamp(rows: Iterable[dict[str, Any]], key: str = "open_time_ms") -> list[dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        indexed[int(row[key])] = row
    return [indexed[timestamp] for timestamp in sorted(indexed)]


def gap_report(timestamps: Sequence[int], interval_ms: int) -> dict[str, Any]:
    ordered = sorted(set(int(value) for value in timestamps))
    gaps: list[dict[str, int]] = []
    for left, right in zip(ordered, ordered[1:]):
        delta = right - left
        if delta != interval_ms:
            missing = max(0, delta // interval_ms - 1)
            gaps.append({"left_ms": left, "right_ms": right, "missing_intervals": missing})
    return {
        "rows": len(ordered),
        "duplicate_count": len(timestamps) - len(ordered),
        "gap_count": len(gaps),
        "missing_interval_count": sum(item["missing_intervals"] for item in gaps),
        "gaps_preview": gaps[:20],
    }


def to_float(value: Any, default: float | None = None) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def rolling_mean(values: Sequence[float | None], window: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    total = 0.0
    queue: list[float] = []
    for index, value in enumerate(values):
        if value is None:
            queue.append(float("nan"))
        else:
            queue.append(float(value))
            total += float(value)
        if len(queue) > window:
            removed = queue.pop(0)
            if math.isfinite(removed):
                total -= removed
        if len(queue) == window and all(math.isfinite(item) for item in queue):
            result[index] = total / window
    return result


def rolling_std(values: Sequence[float | None], window: int) -> list[float | None]:
    result: list[float | None] = [None] * len(values)
    for index in range(window - 1, len(values)):
        sample = values[index - window + 1 : index + 1]
        if all(item is not None and math.isfinite(float(item)) for item in sample):
            result[index] = statistics.pstdev(float(item) for item in sample)
    return result


def lag_return(closes: Sequence[float], lag: int) -> list[float | None]:
    output: list[float | None] = [None] * len(closes)
    for index in range(lag, len(closes)):
        left = closes[index - lag]
        right = closes[index]
        if left > 0 and right > 0:
            output[index] = math.log(right / left)
    return output


def forward_return(closes: Sequence[float], index: int, horizon: int) -> float | None:
    target = index + horizon
    if index < 0 or target >= len(closes):
        return None
    left, right = closes[index], closes[target]
    if left <= 0 or right <= 0:
        return None
    return right / left - 1.0


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def one_sided_positive_pvalue(values: Sequence[float]) -> float:
    sample = [float(value) for value in values if math.isfinite(float(value))]
    if len(sample) < 3:
        return 1.0
    mean = statistics.mean(sample)
    sd = statistics.stdev(sample)
    if sd <= 0:
        return 0.0 if mean > 0 else 1.0
    z_score = mean / (sd / math.sqrt(len(sample)))
    return max(0.0, min(1.0, 1.0 - normal_cdf(z_score)))


def holm_bonferroni(pvalues: dict[str, float], alpha: float = 0.05) -> dict[str, Any]:
    ordered = sorted(pvalues.items(), key=lambda item: (item[1], item[0]))
    adjusted: dict[str, float] = {}
    running = 0.0
    total = len(ordered)
    rejected: list[str] = []
    stop = False
    for rank, (key, pvalue) in enumerate(ordered, start=1):
        multiplier = total - rank + 1
        raw_adjusted = min(1.0, pvalue * multiplier)
        running = max(running, raw_adjusted)
        adjusted[key] = running
        threshold = alpha / multiplier
        if not stop and pvalue <= threshold:
            rejected.append(key)
        else:
            stop = True
    return {
        "method": "HOLM_BONFERRONI",
        "alpha": alpha,
        "raw_pvalues": dict(pvalues),
        "adjusted_pvalues": adjusted,
        "rejected_ids": rejected,
        "rejected_count": len(rejected),
    }


def confidence_interval_per_10000(values: Sequence[float]) -> dict[str, float | int]:
    sample = [float(value) for value in values if math.isfinite(float(value))]
    if not sample:
        return {
            "count": 0,
            "mean_per_10000_brl": 0.0,
            "lower_95_per_10000_brl": 0.0,
            "upper_95_per_10000_brl": 0.0,
        }
    mean = statistics.mean(sample)
    if len(sample) == 1:
        margin = 0.0
    else:
        margin = 1.96 * statistics.stdev(sample) / math.sqrt(len(sample))
    return {
        "count": len(sample),
        "mean_per_10000_brl": mean * 10000,
        "lower_95_per_10000_brl": (mean - margin) * 10000,
        "upper_95_per_10000_brl": (mean + margin) * 10000,
    }


def merge_asof(
    timestamps: Sequence[int],
    source_timestamps: Sequence[int],
    source_values: Sequence[float],
) -> list[float | None]:
    output: list[float | None] = []
    for timestamp in timestamps:
        position = bisect_right(source_timestamps, timestamp) - 1
        output.append(source_values[position] if position >= 0 else None)
    return output


def render_simple_portal(
    *,
    title: str,
    summary_cards: Sequence[tuple[str, str]],
    headings: dict[str, str],
    visual_map: str,
    detail_json: dict[str, Any],
) -> str:
    missing = [heading for heading in REQUIRED_PORTAL_HEADINGS if heading not in headings]
    if missing:
        raise ValueError(f"Missing required portal headings: {missing}")
    cards = "\n".join(
        f"<article class='card'><h3>{label}</h3><p>{value}</p></article>"
        for label, value in summary_cards
    )
    sections = "\n".join(
        f"<section><h2>{heading}</h2><p>{headings[heading]}</p></section>"
        for heading in REQUIRED_PORTAL_HEADINGS
    )
    escaped = (
        json.dumps(detail_json, indent=2, ensure_ascii=False)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{--bg:#07111f;--panel:#0f1f33;--ink:#f3f7fb;--muted:#a9bdd1;--line:#2a4763;--good:#5bd4a8;--warn:#ffd166;--bad:#ff7b7b}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(135deg,#07111f,#0b1727 60%,#10253a);color:var(--ink);font-family:Arial,Helvetica,sans-serif}}
main{{max-width:1180px;margin:auto;padding:28px}} h1{{font-size:clamp(28px,4vw,52px);margin:0 0 8px}} .subtitle{{color:var(--muted);font-size:18px}}
.lock{{border:2px solid var(--bad);background:#28131a;padding:14px 18px;border-radius:14px;font-weight:700;margin:20px 0}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin:20px 0}} .card,section,.map,details{{background:rgba(15,31,51,.96);border:1px solid var(--line);border-radius:16px;padding:18px}}
.card h3{{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.08em;margin:0 0 10px}} .card p{{font-size:22px;margin:0;font-weight:700}}
section{{margin:14px 0}} section h2{{font-size:17px;color:#9dd8ff;margin:0 0 10px}} section p{{font-size:17px;line-height:1.55;margin:0}}
.map{{margin:20px 0;white-space:pre-wrap;font-family:Consolas,monospace;font-size:16px;line-height:1.6;border-color:var(--warn)}} .here{{color:var(--warn);font-weight:800}}
pre{{white-space:pre-wrap;word-break:break-word;color:#d9e8f5}} summary{{cursor:pointer;font-weight:700}}
footer{{color:var(--muted);padding:20px 0 40px}}
</style>
</head>
<body><main>
<h1>{title}</h1>
<p class="subtitle">Pesquisa histórica controlada. Nenhuma ordem, recomendação, alocação ou uso de capital.</p>
<div class="lock">BLOCKED_RESEARCH_ONLY · NO_ACTION_RESEARCH_ONLY · posição = 0 · capital = R$ 0</div>
<div class="grid">{cards}</div>
<div class="map"><span class="here">VOCE ESTA AQUI</span>\n{visual_map}</div>
{sections}
<details><summary>Detalhes técnicos auditáveis</summary><pre>{escaped}</pre></details>
<footer>Um resultado histórico positivo não autoriza execução. O sistema permanece bloqueado para decisão e capital.</footer>
</main></body></html>"""
