"""Validate only the frozen V2A/Delta inputs consumed by Bull Replay."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.gate_btc_bull_replay_live_shadow import LiveShadowError, parse_source


def validate_source(v2a_zip: Path, delta_zip: Path, expected_close: str) -> dict:
    source = parse_source(v2a_zip, delta_zip)
    if source['data_as_of'] != expected_close:
        raise LiveShadowError(f"expected close {expected_close}, got {source['data_as_of']}")
    components = {}
    for name, version in (('v2a', 'V2A_FROZEN_REPLAY_1.0'), ('delta', 'DELTA_FROZEN_REPLAY_1.0')):
        manifest = source[f'{name}_manifest']
        required = {
            'wrapper_version': version,
            'mode': 'frozen_public_input_no_network',
            'technical_status': 'PASS',
            'data_quality_status': 'PASS',
            'operational_status': 'NOT_APPROVED',
            'real_orders': 0,
            'capital_used': 0,
        }
        for key, value in required.items():
            actual = manifest.get(key)
            if actual != value or (key in ('real_orders', 'capital_used') and isinstance(actual, bool)):
                raise LiveShadowError(f'unsafe {name} source {key}: {actual!r}')
        components[name] = {'status': 'PASS', 'sha256': source[f'{name}_sha256']}
    return {
        'schema': 'gate_btc.bull_replay_source_boundary.v1',
        'status': 'PASS', 'data_cutoff': expected_close,
        'research_only': True, 'operational_status': 'NOT_APPROVED',
        'orders_generated': 0, 'real_capital_used': 0, 'methodology_changes': 0,
        'scientific_credit': False, 'engine_feed': False,
        'scope': 'V2A_AND_DELTA_ONLY', 'components': components,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--v2a-zip', type=Path, required=True)
    parser.add_argument('--delta-zip', type=Path, required=True)
    parser.add_argument('--expected-close', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = validate_source(args.v2a_zip, args.delta_zip, args.expected_close)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
