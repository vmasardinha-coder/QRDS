#!/usr/bin/env python3
"""Skip known B3 non-session dates before intraday source probing; no eligibility."""
import argparse
import json
from datetime import date

SOURCE = 'https://www.b3.com.br/pt_br/noticias/calendario-de-negociacao-da-b3-confira-o-funcionamento-da-bolsa-em-2026.htm'
OCTOBER_CONFIRMATION = 'https://b3.com.br/pt_br/noticias/confira-o-funcionamento-da-b3-no-feriado-de-nossa-senhora-aparecida.htm'
CLOSED_2026 = frozenset([
    '2026-01-01', '2026-02-16', '2026-02-17', '2026-04-03',
    '2026-04-21', '2026-05-01', '2026-06-04', '2026-09-07',
    '2026-10-12', '2026-11-02', '2026-11-20', '2026-12-24',
    '2026-12-25', '2026-12-31',
])

def evaluate(day):
    day = date.fromisoformat(day)
    if day.weekday() >= 5:
        reason = 'WEEKEND'
    elif day.isoformat() in CLOSED_2026:
        reason = 'OFFICIAL_B3_CLOSED_2026'
    else:
        reason = 'NOT_A_KNOWN_NON_SESSION_CONTINUE_EXISTING_SOURCE_GUARDS'
    skip = reason in ('WEEKEND', 'OFFICIAL_B3_CLOSED_2026')
    return {
        'schema': 'qrds.b3.intraday_calendar_guard.v1',
        'date': day.isoformat(),
        'decision': 'SKIP_KNOWN_NON_SESSION' if skip else 'CONTINUE_EXISTING_SOURCE_GUARDS',
        'reason': reason,
        'source_url': SOURCE,
        'october_confirmation_url': OCTOBER_CONFIRMATION if day.isoformat() == '2026-10-12' else None,
        'does_not_assert_live_source_ready': True,
        'eligible_observation_increment': 0,
        'scientific_credit': 0,
        'orders': 0,
        'real_capital': 0,
        'engine_feed': False,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--date', required=True)
    a = p.parse_args()
    print(json.dumps(evaluate(a.date), sort_keys=True))

if __name__ == '__main__':
    main()
