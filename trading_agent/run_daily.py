"""Ponto de entrada do ciclo diario: python -m trading_agent.run_daily"""

from __future__ import annotations

import sys
import traceback

from . import charts, data_sources, engine, portal, report

SLEEVE_RUNNERS = {
    "equities": engine.run_equities,
    "crypto": engine.run_crypto,
    "b3": engine.run_b3,
    "b3_estruturadas": engine.run_b3_structured,
}


def main() -> int:
    today = engine.today_utc()
    results: dict[str, dict] = {}
    errors: dict[str, str] = {}
    source_failures: dict[str, dict] = {}

    for name, runner in SLEEVE_RUNNERS.items():
        try:
            results[name] = runner(today)
        except Exception as err:  # noqa: BLE001 - o relatorio regista a falha
            errors[name] = str(err)
            source_failures[name] = dict(data_sources.FAILURE_TALLY)
            traceback.print_exc()

    content = report.build_report(today, results, errors, source_failures)
    path = report.write_report(today, content)
    print(f"Relatorio escrito em {path}")

    if results:
        chart_path = charts.write_chart(today, report.chart_panels(results),
                                        report.REPORTS_DIR)
        print(f"Grafico escrito em {chart_path}")

    # O portal e camada de leitura: se rebentar, o ciclo ja entregou o
    # relatorio e o grafico, e derrubar a execucao por causa da vista bonita
    # seria trocar o que importa pelo que ajuda.
    try:
        portal_path = portal.write_portal(today, results, errors,
                                          source_failures, report.REPORTS_DIR)
        print(f"Portal escrito em {portal_path}")
    except Exception:  # noqa: BLE001 - nunca derruba o ciclo
        print("AVISO: portal nao foi gerado (relatorio e grafico intactos).",
              file=sys.stderr)
        traceback.print_exc()

    if not results:
        print("FALHA: nenhuma carteira executou.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
