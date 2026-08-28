#!/usr/bin/env python3
"""Deterministic V16B canonical calendar resolver.

Operational calendar only. It encodes the already-frozen V16B clock:
Thursday SIGNAL -> Friday ENTRY -> COMPLETE EXIT eight days after SIGNAL,
anchored at the preregistered 2026-08-27 window. It never creates a late
seal and never moves a missed window backward.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, timedelta

ANCHOR_SIGNAL = date(2026, 8, 27)  # frozen/preregistered SIGNAL anchor
WEEK_DAYS = 7
ENTRY_OFFSET_DAYS = 1
EXIT_OFFSET_DAYS = 8


@dataclass(frozen=True)
class Window:
    signal_date: date
    entry_date: date
    complete_exit_date: date

    def as_dict(self) -> dict:
        return {
            "signal_date": self.signal_date.isoformat(),
            "entry_date": self.entry_date.isoformat(),
            "complete_exit_date": self.complete_exit_date.isoformat(),
            "anchor_signal_date": ANCHOR_SIGNAL.isoformat(),
            "cadence_days": WEEK_DAYS,
            "calendar_authority": "FROZEN_WEEKLY_V16B_CLOCK",
            "no_backfill": True,
            "no_late_seal": True,
        }


def window_from_signal(signal: date) -> Window:
    delta = (signal - ANCHOR_SIGNAL).days
    if delta < 0 or delta % WEEK_DAYS:
        raise ValueError("signal date is not on the frozen V16B weekly clock")
    return Window(
        signal_date=signal,
        entry_date=signal + timedelta(days=ENTRY_OFFSET_DAYS),
        complete_exit_date=signal + timedelta(days=EXIT_OFFSET_DAYS),
    )


def next_unmissed_window(as_of: date) -> Window:
    """Return the first SIGNAL window whose signal clock has not passed.

    If ``as_of`` is after a SIGNAL date, that cycle is never reconstructed;
    resolution advances to the next frozen weekly window.
    """
    if as_of <= ANCHOR_SIGNAL:
        return window_from_signal(ANCHOR_SIGNAL)
    days = (as_of - ANCHOR_SIGNAL).days
    weeks = (days + WEEK_DAYS - 1) // WEEK_DAYS
    signal = ANCHOR_SIGNAL + timedelta(days=weeks * WEEK_DAYS)
    if signal < as_of:
        signal += timedelta(days=WEEK_DAYS)
    return window_from_signal(signal)


def window_for_entry_date(entry_date: date) -> Window:
    return window_from_signal(entry_date - timedelta(days=ENTRY_OFFSET_DAYS))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--as-of", required=True, help="UTC YYYY-MM-DD")
    p.add_argument(
        "--role",
        choices=("next", "signal", "entry"),
        default="next",
        help="next unresolved window, exact SIGNAL day, or exact ENTRY day",
    )
    a = p.parse_args()
    as_of = date.fromisoformat(a.as_of)
    if a.role == "entry":
        w = window_for_entry_date(as_of)
    elif a.role == "signal":
        w = window_from_signal(as_of)
    else:
        w = next_unmissed_window(as_of)
    print(json.dumps(w.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
