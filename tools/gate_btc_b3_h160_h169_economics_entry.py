#!/usr/bin/env python3
from __future__ import annotations

import argparse

import gate_btc_b3_h160_h169_economics as impl

# Coverage is a source-availability gate, not a signal-availability gate.
# A zero/undefined rolling scale may legitimately suppress a standardized signal
# without implying that the official causal input is missing.
impl.FAMILY_INPUTS = {
    "H160": ("h160",),
    "H161": ("h161",),
    "H162": ("h162",),
    "H163": ("sofr_volumeInBillions",),
    "H164": ("effr_volumeInBillions",),
    "H165": ("sofr_width",),
    "H166": ("effr_width",),
    "H167": ("volume_ratio",),
    "H168": ("h160", "h161", "h162"),
    "H169": ("h160", "h161", "h162", "sofr_volumeInBillions", "effr_volumeInBillions"),
}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--cells", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    impl.main(a.out, a.ledger, a.cells, a.manifest)


if __name__ == "__main__":
    main()
