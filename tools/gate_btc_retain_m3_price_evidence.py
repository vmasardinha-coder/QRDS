#!/usr/bin/env python3
"""Stage only original M3 price archives after verifying their sealed manifests."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

def retain(runtime_root):
    runtime_root = Path(runtime_root).resolve()
    root = runtime_root / 'runtime/ledgers/momentum_m3_economics'
    archives = sorted(root.glob('source_prices/*/required_prices.zip'))
    archives += sorted(root.glob('epochs/*/source_prices/*/required_prices.zip'))
    verified = []
    for archive in archives:
        manifest = json.loads(archive.with_name('MANIFEST.json').read_text(encoding='utf-8-sig'))
        actual = hashlib.sha256(archive.read_bytes()).hexdigest()
        if actual != manifest.get('prices_zip_sha256'):
            raise ValueError('SEALED_M3_PRICE_ARCHIVE_CHANGED:' + str(archive.relative_to(runtime_root)))
        verified.append(str(archive.relative_to(runtime_root)))
    # Verify all candidates before staging any. Do not recreate missing history.
    if verified:
        subprocess.run(['git', '-C', str(runtime_root), 'add', '-f', '--', *verified], check=True)
    return verified

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime-root', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps({'verified_original_archives_staged': retain(args.runtime_root)}))

if __name__ == '__main__':
    main()
