#!/usr/bin/env python3
"""Thin runner that injects hardened public CMC PIT collection into the definitive study."""
from __future__ import annotations

from tools import gate_btc_cmc_pit_collector as cmc_collector
from tools import gate_btc_cmc_pit_parser as cmc_parser
from tools import gate_btc_survivorship_definitive_pit as definitive


def main() -> int:
    definitive.parse_cmc_html = cmc_parser.parse_cmc_html
    definitive.collect_snapshots = cmc_collector.collect_snapshots
    return definitive.main()


if __name__ == "__main__":
    raise SystemExit(main())
