"""Ponto de entrada do ciclo diario: python -m trading_agent.run_daily"""

from __future__ import annotations

import sys
import traceback

from . import engine, report

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

    for name, runner in SLEEVE_RUNNERS.items():
        try:
            results[name] = runner(today)
        except Exception as err:  # noqa: BLE001 - o relatorio regista a falha
            errors[name] = str(err)
            traceback.print_exc()

    content = report.build_report(today, results, errors)
    path = report.write_report(today, content)
    print(f"Relatorio escrito em {path}")

    if not results:
        print("FALHA: nenhuma carteira executou.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
