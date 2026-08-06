"""Ponto de entrada do ciclo diario: python -m trading_agent.run_daily"""

from __future__ import annotations

import sys
import traceback

from . import engine, report


def main() -> int:
    today = engine.today_utc()
    equities = crypto = None
    equities_error = crypto_error = None

    try:
        equities = engine.run_equities(today)
    except Exception as err:  # noqa: BLE001 - o relatorio regista a falha
        equities_error = str(err)
        traceback.print_exc()

    try:
        crypto = engine.run_crypto(today)
    except Exception as err:  # noqa: BLE001
        crypto_error = str(err)
        traceback.print_exc()

    content = report.build_report(today, equities, crypto, equities_error, crypto_error)
    path = report.write_report(today, content)
    print(f"Relatorio escrito em {path}")

    if equities is None and crypto is None:
        print("FALHA: nenhuma carteira executou.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
