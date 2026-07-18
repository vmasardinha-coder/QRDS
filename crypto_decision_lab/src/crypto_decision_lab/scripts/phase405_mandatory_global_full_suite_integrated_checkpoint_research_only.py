from __future__ import annotations

import argparse
from pathlib import Path

from crypto_decision_lab.scripts.phase396_405_release_reliability_common import (
    build_phase,
)

PHASE = 405


def build(
    *input_paths: Path,
    output_dir: Path,
    project_root: Path,
    git_root: Path,
):
    return build_phase(
        PHASE,
        [Path(path) for path in input_paths],
        Path(output_dir),
        project_root=Path(project_root),
        git_root=Path(git_root),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--git-root", required=True)
    args = parser.parse_args()
    build(
        *[Path(value) for value in args.input],
        output_dir=Path(args.output_dir),
        project_root=Path(args.project_root),
        git_root=Path(args.git_root),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
