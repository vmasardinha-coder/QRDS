"""Wait only for today's frozen window; never alter decision or entry clocks."""
from datetime import datetime, timedelta, timezone
import time
import argparse
import json
from gate_btc_xagent_spot_experiment import load_contract, timestamp


def wait_for_window(now_fn=None, sleep_fn=None, max_wait_seconds=900):
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    sleep_fn = sleep_fn or time.sleep
    c = load_contract()
    first = now_fn()
    start = timestamp(first.date().isoformat()+'T'+c['decision_window_utc'][0]+'Z')
    end = timestamp(first.date().isoformat()+'T'+c['decision_window_utc'][1]+'Z')
    # Outside the pre-start runway, return immediately. The experiment can
    # refresh/mature older outcomes, but its own immutable clock forbids decisions.
    if not start-timedelta(seconds=max_wait_seconds) <= first < start:
        return {'status': 'NO_WAIT_CURRENT_CLOCK', 'now_utc': first.isoformat()}
    while True:
        now = now_fn()
        if now >= start:
            if now > end:
                raise ValueError('MISSED_WINDOW_NO_BACKFILL')
            return {'status': 'FROZEN_WINDOW_OPEN', 'now_utc': now.isoformat()}
        if (now-first).total_seconds() > max_wait_seconds:
            raise ValueError('BOUNDED_WAIT_EXHAUSTED')
        sleep_fn(min(30.0, (start-now).total_seconds()))


if __name__ == '__main__':
    argparse.ArgumentParser().parse_args()
    print(json.dumps(wait_for_window(), sort_keys=True))
