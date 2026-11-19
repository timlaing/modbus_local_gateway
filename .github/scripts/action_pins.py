"""Validate actual YAML action invocations, including quoted and folded values."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any

import yaml


def invalid_references(document: dict[str, Any]) -> list[str]:
    """Return remote action/workflow references without immutable full SHAs."""
    invalid = []
    for job in document.get("jobs", {}).values():
        for item in [job, *job.get("steps", [])]:
            reference = item.get("uses")
            if reference is None or reference.startswith("./"):
                continue
            if re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", reference) is None:
                invalid.append(reference)
    return invalid


WORKFLOW_DIR = Path(__file__).resolve().parents[1] / "workflows"


def main() -> None:
    """Check workflow files without matching examples embedded in run scripts."""
    paths = sorted(WORKFLOW_DIR.glob("*y*ml"))
    if not paths:
        raise SystemExit("No workflow files found")
    for path in paths:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        invalid = invalid_references(document)
        if invalid:
            raise SystemExit(f"Unpinned references in {path}: {invalid}")


if __name__ == "__main__":
    main()
