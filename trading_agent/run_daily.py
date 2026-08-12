"""Ponto de entrada do ciclo diario: python -m trading_agent.run_daily"""

from __future__ import annotations

import sys
import traceback

from . import charts, data_sources, engine, report

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

    if not results:
        print("FALHA: nenhuma carteira executou.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
