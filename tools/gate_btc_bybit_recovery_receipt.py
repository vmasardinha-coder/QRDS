"""Classify exact Bybit recovery job execution; workflow success is insufficient."""
import argparse
import json
from pathlib import Path


def classify(run, jobs):
    if (run.get('name') != 'GATE BTC Bybit Spot Recovery Audit' or
            run.get('head_branch') != 'main' or run.get('status') != 'completed' or
            run.get('conclusion') != 'success'):
        raise ValueError('BYBIT_RECOVERY_RUN_IDENTITY_OR_SUCCESS_MISMATCH')
    actual = [job for job in jobs.get('jobs', [])
              if job.get('name') == 'bybit-spot-recovery-audit']
    if len(actual) != 1 or actual[0].get('status') != 'completed':
        raise ValueError('BYBIT_RECOVERY_JOB_RECEIPT_MISSING_OR_AMBIGUOUS')
    job = actual[0]
    if job.get('run_id') != run.get('id'):
        raise ValueError('BYBIT_RECOVERY_JOB_RUN_MISMATCH')
    if job.get('conclusion') not in ('success', 'skipped'):
        raise ValueError('BYBIT_RECOVERY_JOB_NOT_SUCCESSFUL')
    eligible = job['conclusion'] == 'success'
    return {
        'schema': 'gate_btc.bybit_recovery_dependency_receipt.v1',
        'status': 'RECOVERY_JOB_EXECUTED' if eligible else 'WAIT_UPSTREAM_RECOVERY_JOB_SKIPPED',
        'eligible': eligible, 'source_run_id': run['id'], 'source_job_id': job['id'],
        'source_job_conclusion': job['conclusion'], 'evidence_role': 'DEPENDENCY_RECEIPT_ONLY',
        'research_only': True, 'shadow_only': True, 'not_approved': True,
        'engine_feed': False, 'orders_generated': 0, 'real_capital_used': 0,
        'scientific_credit': 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--jobs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path, required=True)
    args = parser.parse_args()
    receipt = classify(json.loads(args.run.read_text()), json.loads(args.jobs.read_text()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    with args.github_output.open('a') as output:
        output.write('eligible=' + str(receipt['eligible']).lower() + '\n')
    print(json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
