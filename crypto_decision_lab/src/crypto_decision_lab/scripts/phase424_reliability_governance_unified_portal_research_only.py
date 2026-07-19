from __future__ import annotations

from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase416_425_reliability_governance_common import (
    build_phase,
)

PHASE = 424


def build(
    *input_paths: Path,
    output_dir: Path,
    project_root: Path,
    git_root: Path,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return build_phase(
        PHASE,
        list(input_paths),
        output_dir,
        project_root=project_root,
        git_root=git_root,
        context=context,
    )
