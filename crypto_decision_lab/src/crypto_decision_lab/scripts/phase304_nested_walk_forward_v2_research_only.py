from __future__ import annotations

import argparse
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import (
    REQUIRED_PORTAL_HEADINGS,
    ROOT,
    base_payload,
    confidence_interval_per_10000,
    fingerprint,
    holm_bonferroni,
    one_sided_positive_pvalue,
    read_csv_gz,
    read_json,
    render_simple_portal,
    to_float,
    write_json,
    write_text,
)

HOUR_MS = 60 * 60 * 1000


def _numeric(row: dict[str, str], key: str) -> float | None:
    return to_float(row.get(key))


def _signal(
    hypothesis: dict[str, Any],
    index: int,
    rows: list[dict[str, str]],
    closes: list[float],
) -> int:
    family = hypothesis["family"]
    threshold = float(hypothesis["threshold"])
    lookback = int(hypothesis["lookback_hours"])
    if index < max(lookback, 24):
        return 0

    if family in {"MEAN_REVERSION", "MOMENTUM"}:
        value = closes[index] / closes[index - lookback] - 1.0
        if abs(value) < threshold:
            return 0
        sign = 1 if value > 0 else -1
        return -sign if family == "MEAN_REVERSION" else sign

    if family == "TREND":
        feature = _numeric(rows[index], hypothesis["feature"])
        if feature is None or abs(feature) < threshold:
            return 0
        return 1 if feature > 0 else -1

    if family == "DERIVATIVES_CONTRARIAN":
        feature = _numeric(rows[index], "funding_mean_3")
        if feature is None or abs(feature) < threshold:
            return 0
        return -1 if feature > 0 else 1

    if family == "DERIVATIVES_MOMENTUM":
        oi = _numeric(rows[index], "open_interest_change_24h")
        price = _numeric(rows[index], "return_24h")
        if oi is None or price is None or abs(oi) < threshold or abs(price) < 0.001:
            return 0
        if oi * price <= 0:
            return 0
        return 1 if price > 0 else -1

    raise ValueError(f"Unsupported family: {family}")


def _trades(
    hypothesis: dict[str, Any],
    rows: list[dict[str, str]],
    closes: list[float],
    start: int,
    end: int,
    cost_bps: int,
) -> list[dict[str, Any]]:
    holding = int(hypothesis["holding_hours"])
    cost = cost_bps / 10000.0
    output: list[dict[str, Any]] = []
    index = max(start, 168)
    final_entry = min(end, len(rows) - holding - 1)
    while index <= final_entry:
        direction = _signal(hypothesis, index, rows, closes)
        if direction == 0:
            index += 1
            continue
        gross = direction * (closes[index + holding] / closes[index] - 1.0)
        net = gross - cost
        vol = _numeric(rows[index], "realized_vol_24h") or 0.0
        ret24 = _numeric(rows[index], "return_24h") or 0.0
        if vol > 0 and abs(ret24) > 1.5 * vol:
            regime = "TREND"
        elif vol > 0.012:
            regime = "HIGH_VOL"
        else:
            regime = "RANGE"
        output.append(
            {
                "entry_index": index,
                "exit_index": index + holding,
                "entry_time_ms": int(rows[index]["open_time_ms"]),
                "direction": direction,
                "gross_return": gross,
                "net_return": net,
                "regime": regime,
            }
        )
        index += holding
    return output


def _metrics(trades: list[dict[str, Any]]) -> dict[str, Any]:
    values = [float(item["net_return"]) for item in trades]
    ci = confidence_interval_per_10000(values)
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    wins = 0
    for value in values:
        equity *= 1.0 + value
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = min(max_drawdown, equity / peak - 1.0)
        if value > 0:
            wins += 1
    return {
        **ci,
        "trade_count": len(values),
        "win_rate": wins / len(values) if values else 0.0,
        "compounded_return": equity - 1.0,
        "max_drawdown": max_drawdown,
        "pvalue_positive": one_sided_positive_pvalue(values),
    }


def _folds(length: int) -> list[dict[str, int]]:
    minimum_train = 365 * 24
    test_size = 90 * 24
    embargo = 24
    folds: list[dict[str, int]] = []
    test_start = minimum_train
    while test_start + test_size <= length:
        train_end = test_start - embargo
        inner_size = min(90 * 24, max(30 * 24, train_end // 5))
        inner_start = train_end - inner_size
        folds.append(
            {
                "train_start": 168,
                "train_end": inner_start - 1,
                "inner_start": inner_start,
                "inner_end": train_end - 1,
                "outer_start": test_start,
                "outer_end": test_start + test_size - 1,
                "embargo_hours": embargo,
            }
        )
        test_start += test_size
    if len(folds) > 8:
        folds = folds[-8:]
    return folds


def _evaluate_inner(
    hypotheses: list[dict[str, Any]],
    rows: list[dict[str, str]],
    closes: list[float],
    fold: dict[str, int],
) -> tuple[dict[str, Any], dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    pvalues: dict[str, float] = {}
    for hypothesis in hypotheses:
        trades = _trades(
            hypothesis,
            rows,
            closes,
            fold["inner_start"],
            fold["inner_end"],
            10,
        )
        metrics = _metrics(trades)
        results[hypothesis["hypothesis_id"]] = metrics
        pvalues[hypothesis["hypothesis_id"]] = float(metrics["pvalue_positive"])
    penalty = holm_bonferroni(pvalues)
    ranked = sorted(
        hypotheses,
        key=lambda item: (
            results[item["hypothesis_id"]]["lower_95_per_10000_brl"],
            results[item["hypothesis_id"]]["mean_per_10000_brl"],
            results[item["hypothesis_id"]]["trade_count"],
            item["hypothesis_id"],
        ),
        reverse=True,
    )
    selected = ranked[0]
    return selected, {
        "results": results,
        "multiple_testing": penalty,
        "selected_id": selected["hypothesis_id"],
    }


def _plain_money(value: float) -> str:
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    return f"R$ {sign}{absolute:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def build(
    phase302_path: Path,
    phase303_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    phase302 = read_json(phase302_path)
    phase303 = read_json(phase303_path)
    if phase302.get("phase") != 302 or phase303.get("phase") != 303:
        raise RuntimeError("Phase 302 or 303 artifact is invalid.")
    if not phase303.get("registry_closed"):
        raise RuntimeError("Hypothesis registry must be closed before evaluation.")

    matrix_path = ROOT / phase302["matrix_path"]
    rows = read_csv_gz(matrix_path)
    rows.sort(key=lambda row: int(row["open_time_ms"]))
    closes = []
    for row in rows:
        value = _numeric(row, "close")
        if value is None or value <= 0:
            raise ValueError("Invalid close in feature matrix.")
        closes.append(value)

    hypotheses = phase303["hypotheses"]
    folds = _folds(len(rows))
    if len(folds) < 3:
        raise RuntimeError(
            f"Insufficient history for nested walk-forward: {len(rows)} rows produced {len(folds)} folds."
        )

    fold_results: list[dict[str, Any]] = []
    selections: list[str] = []
    outer_trade_values: list[float] = []
    regime_values: dict[str, list[float]] = defaultdict(list)
    cost_results: dict[int, list[float]] = {5: [], 10: [], 20: []}
    all_inner_pvalues: dict[str, list[float]] = defaultdict(list)

    by_id = {item["hypothesis_id"]: item for item in hypotheses}
    for number, fold in enumerate(folds, start=1):
        selected, inner = _evaluate_inner(hypotheses, rows, closes, fold)
        selected_id = selected["hypothesis_id"]
        selections.append(selected_id)
        for hypothesis_id, metrics in inner["results"].items():
            all_inner_pvalues[hypothesis_id].append(float(metrics["pvalue_positive"]))

        fold_cost_metrics: dict[str, Any] = {}
        outer_trades_10: list[dict[str, Any]] = []
        for cost_bps in (5, 10, 20):
            trades = _trades(
                selected,
                rows,
                closes,
                fold["outer_start"],
                fold["outer_end"],
                cost_bps,
            )
            metrics = _metrics(trades)
            fold_cost_metrics[str(cost_bps)] = metrics
            cost_results[cost_bps].extend(float(item["net_return"]) for item in trades)
            if cost_bps == 10:
                outer_trades_10 = trades

        for trade in outer_trades_10:
            value = float(trade["net_return"])
            outer_trade_values.append(value)
            regime_values[str(trade["regime"])].append(value)

        fold_results.append(
            {
                "fold": number,
                **fold,
                "selected_hypothesis_id": selected_id,
                "selected_family": selected["family"],
                "inner_selection": inner,
                "outer_cost_metrics": fold_cost_metrics,
            }
        )

    modal_id, modal_count = Counter(selections).most_common(1)[0]
    selection_share = modal_count / len(selections)
    selection_stable = selection_share >= 0.70
    outer_metrics = _metrics(
        [{"net_return": value} for value in outer_trade_values]
    )
    regime_metrics = {
        regime: _metrics([{"net_return": value} for value in values])
        for regime, values in sorted(regime_values.items())
    }
    aggregate_cost_metrics = {
        str(cost): _metrics([{"net_return": value} for value in values])
        for cost, values in cost_results.items()
    }

    averaged_pvalues = {
        hypothesis_id: statistics.mean(values)
        for hypothesis_id, values in all_inner_pvalues.items()
    }
    global_penalty = holm_bonferroni(averaged_pvalues)
    multiple_testing_survivors = global_penalty["rejected_ids"]
    survives_penalty = modal_id in multiple_testing_survivors
    all_cost_positive_lower = all(
        metrics["lower_95_per_10000_brl"] > 0
        for metrics in aggregate_cost_metrics.values()
    )
    all_regimes_positive_mean = bool(regime_metrics) and all(
        metrics["mean_per_10000_brl"] > 0
        for metrics in regime_metrics.values()
    )
    robustness_pass = (
        selection_stable
        and survives_penalty
        and all_cost_positive_lower
        and all_regimes_positive_mean
        and outer_metrics["trade_count"] >= 50
    )

    payload = base_payload(304, "NESTED_WALK_FORWARD_V2_EVALUATED_RESEARCH_ONLY")
    payload.update(
        {
            "gate": "PHASE304_NESTED_WALK_FORWARD_V2_READY_RESEARCH_ONLY",
            "phase302_artifact": phase302_path.relative_to(ROOT).as_posix(),
            "phase302_fingerprint": phase302["artifact_fingerprint"],
            "phase303_artifact": phase303_path.relative_to(ROOT).as_posix(),
            "phase303_fingerprint": phase303["artifact_fingerprint"],
            "row_count": len(rows),
            "fold_count": len(folds),
            "nested_walk_forward": True,
            "outer_data_used_for_selection": False,
            "embargo_hours": 24,
            "selection_history": selections,
            "modal_hypothesis_id": modal_id,
            "modal_hypothesis_family": by_id[modal_id]["family"],
            "modal_selection_share": selection_share,
            "selection_stable": selection_stable,
            "multiple_testing": global_penalty,
            "modal_survives_multiple_testing": survives_penalty,
            "outer_metrics_10bps": outer_metrics,
            "cost_robustness": aggregate_cost_metrics,
            "regime_robustness": regime_metrics,
            "robustness_pass": robustness_pass,
            "historical_research_candidate_only": robustness_pass,
            "strategy_approved": False,
            "forward_shadow_eligible": False,
            "forward_shadow_started": False,
            "paper_trading_started": False,
            "automatic_promotion": False,
            "fold_results": fold_results,
            "conclusion": (
                "HISTORICAL_RESEARCH_CANDIDATE_ONLY_NO_EXECUTION"
                if robustness_pass
                else "NO_ACTION_RESEARCH_ONLY"
            ),
        }
    )
    payload["artifact_fingerprint"] = fingerprint(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / "phase304_nested_walk_forward_v2.json"
    write_json(artifact_path, payload)

    mean_money = float(outer_metrics["mean_per_10000_brl"])
    lower_money = float(outer_metrics["lower_95_per_10000_brl"])
    approved_word = "REPROVADO PARA EXECUCAO"
    headings = {
        "O QUE FOI COLETADO": (
            f"{len(rows):,} candles horários e contexto público de volume, volatilidade, "
            "liquidez e derivativos, quando disponível."
        ).replace(",", "."),
        "O QUE FOI TESTADO": (
            f"{len(hypotheses)} hipóteses pré-registradas em {len(folds)} janelas futuras separadas, "
            "com custos de 5, 10 e 20 pontos-base."
        ),
        "QUAL ERA A PERGUNTA": (
            "Alguma regra permanece positiva fora da amostra, em diferentes regimes e custos, "
            "sem escolher parâmetros olhando o futuro?"
        ),
        "O QUE O RESULTADO SIGNIFICA": (
            f"A hipótese mais escolhida foi {modal_id}. O resultado médio externo, após custo de "
            f"10 bps, equivale a {_plain_money(mean_money)} por R$10.000 por operação modelada; "
            f"o limite inferior de 95% foi {_plain_money(lower_money)}."
        ),
        "EXEMPLO COM R$10.000": (
            f"Em uma operação teórica de R$10.000, a média modelada foi {_plain_money(mean_money)}. "
            "Isso não é promessa, saldo de conta nem autorização para investir."
        ),
        "POR QUE FOI REPROVADO OU APROVADO": (
            f"{approved_word}. Mesmo que a robustez histórica seja {robustness_pass}, a política "
            "permanente proíbe promoção automática; dados passados não iniciam forward shadow."
        ),
        "O QUE O TESTE NAO PROVA": (
            "Não prova lucro futuro, execução real, slippage real, capacidade operacional, "
            "estabilidade futura nem segurança para usar capital."
        ),
        "CONCLUSAO PRATICA": (
            "Continuar pesquisa controlada. Não comprar, não vender, não alocar e não criar ordem. "
            "Estado: NO_ACTION_RESEARCH_ONLY."
        ),
    }
    visual_map = """DADOS PUBLICOS MAIS LONGOS       CONCLUIDO
FEATURES COM LINHAGEM             CONCLUIDO
HIPOTESES FINITAS                 CONCLUIDO
NESTED WALK-FORWARD               CONCLUIDO
>>> VOCE ESTA AQUI: RESULTADO HISTORICO, SEM PROMOCAO
ESTRATEGIA APROVADA               NAO
FORWARD SHADOW                    BLOQUEADO
PAPER TRADING                     BLOQUEADO
CAPITAL REAL                      BLOQUEADO"""
    portal_html = render_simple_portal(
        title="QRDS Phase 304 — Evidência Histórica v2",
        summary_cards=(
            ("Hipóteses", str(len(hypotheses))),
            ("Janelas externas", str(len(folds))),
            ("Candidata modal", modal_id),
            ("Média por R$10.000", _plain_money(mean_money)),
            ("Limite inferior 95%", _plain_money(lower_money)),
            ("Estratégia aprovada", "NÃO"),
        ),
        headings=headings,
        visual_map=visual_map,
        detail_json=payload,
    )
    portal_path = output_dir / "portal/index.html"
    write_text(portal_path, portal_html)
    payload["portal_path"] = portal_path.relative_to(ROOT).as_posix()
    payload["portal_required_headings"] = list(REQUIRED_PORTAL_HEADINGS)
    payload["artifact_fingerprint"] = fingerprint(
        {key: value for key, value in payload.items() if key != "artifact_fingerprint"}
    )
    write_json(artifact_path, payload)

    write_text(
        ROOT / "docs/reports/evidence_v2/phase304_nested_walk_forward_v2_summary.md",
        f"""# Phase 304 — Nested Walk-Forward v2

Gate: `{payload["gate"]}`

- Rows: `{len(rows)}`
- Outer folds: `{len(folds)}`
- Registered hypotheses: `{len(hypotheses)}`
- Modal hypothesis: `{modal_id}`
- Modal selection share: `{selection_share:.2%}`
- Selection stable: `{selection_stable}`
- Modal survives Holm penalty: `{survives_penalty}`
- Robustness pass: `{robustness_pass}`
- Mean modeled result per R$10.000 at 10 bps: `{mean_money:.2f}`
- Lower 95% per R$10.000 at 10 bps: `{lower_money:.2f}`
- Strategy approved: `False`
- Forward shadow eligible: `False`
- Paper trading started: `False`
- Operational: `BLOCKED_RESEARCH_ONLY`
- Conclusion: `{payload["conclusion"]}`

Even a historically positive result remains a research candidate only and cannot
authorize execution.
""",
    )
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase302-artifact",
        type=Path,
        default=ROOT
        / "artifacts/phase302_controlled_feature_registry_v2_research_only/"
        "phase302_controlled_feature_registry_v2.json",
    )
    parser.add_argument(
        "--phase303-artifact",
        type=Path,
        default=ROOT
        / "artifacts/phase303_finite_hypothesis_registry_v2_research_only/"
        "phase303_finite_hypothesis_registry_v2.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "artifacts/phase304_nested_walk_forward_v2_research_only",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build(args.phase302_artifact, args.phase303_artifact, args.output_dir)
    print(payload["gate"])
    print("Rows:", payload["row_count"])
    print("Folds:", payload["fold_count"])
    print("Modal hypothesis:", payload["modal_hypothesis_id"])
    print("Selection stable:", payload["selection_stable"])
    print("Robustness pass:", payload["robustness_pass"])
    print("Strategy approved:", payload["strategy_approved"])
    print("Conclusion:", payload["conclusion"])
    print("Operational:", payload["locks"]["operational_status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
