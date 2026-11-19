#!/usr/bin/env python3

"""Validate GitHub Actions references in the workflow files."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
import os
from pathlib import Path
import re
import sys

import yaml

WORKFLOW_DIR = Path(".github/workflows")

FULL_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")

VERSION_COMMENT_PATTERN = re.compile(r"#\s*v?\d+(?:\.\d+)*\s*$")

IN_CI = "GITHUB_ACTIONS" in os.environ


@dataclass(frozen=True)
class Reference:
    """A single `uses: owner/action@ref` reference."""

    action: str
    ref: str
    path: Path
    line: int
    line_text: str


def mapping_value(node: yaml.Node | None, name: str) -> yaml.Node | None:
    """Read a mapping entry without treating script text as YAML references."""
    if not isinstance(node, yaml.MappingNode):
        return None
    return next((value for key, value in node.value if key.value == name), None)


def reference_nodes(document: yaml.Node | None) -> list[yaml.ScalarNode]:
    """Select only job-level and step-level action invocations."""
    jobs = mapping_value(document, "jobs")
    if not isinstance(jobs, yaml.MappingNode):
        return []
    references: list[yaml.ScalarNode] = []
    for _, job in jobs.value:
        entries = [mapping_value(job, "uses")]
        steps = mapping_value(job, "steps")
        if isinstance(steps, yaml.SequenceNode):
            entries.extend(mapping_value(step, "uses") for step in steps.value)
        references.extend(node for node in entries if isinstance(node, yaml.ScalarNode))
    return references


def collect_references(paths: list[Path]) -> list[Reference]:
    """Parse remote references as complete YAML values and retain line anchors."""
    references: list[Reference] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        for node in reference_nodes(yaml.compose(text, Loader=yaml.SafeLoader)):
            action, separator, ref = node.value.partition("@")
            if not separator or node.value.startswith("./"):
                continue
            if re.fullmatch(r"[\w.-]+(?:/[\w.-]+)+", action) is None:
                continue
            number = node.start_mark.line + 1
            references.append(
                Reference(
                    action=action,
                    ref=ref,
                    path=path,
                    line=number,
                    line_text=lines[number - 1],
                )
            )
    return references


def resolve_paths(paths: list[Path]) -> list[Path]:
    """Expand directories to workflow files, keeping the given order."""
    resolved: list[Path] = []

    for path in paths:
        if path.is_dir():
            resolved.extend(sorted(path.glob("*.y*ml")))
        else:
            resolved.append(path)

    return resolved


def report(level: str, message: str, reference: Reference) -> None:
    """Print a finding, using workflow annotations when running in CI."""
    location = f"{reference.path}:{reference.line}"

    if IN_CI:
        print(
            f"::{level} file={reference.path},line={reference.line}::{message}",
        )
        return

    print(f"{location}: {message}")


def check_sha_pins(references: list[Reference]) -> int:
    """Require immutable, full-length commit SHAs for every remote action."""
    failures = 0
    for reference in references:
        if FULL_SHA_PATTERN.fullmatch(reference.ref):
            continue
        report(
            "error",
            f"{reference.action}@{reference.ref} must use a full "
            "40-character commit SHA",
            reference,
        )
        failures += 1
    return failures


def check_sha_annotations(references: list[Reference]) -> None:
    """Warn when a full-SHA pin lacks the version comment Dependabot reads."""
    for reference in references:
        if not FULL_SHA_PATTERN.match(reference.ref):
            continue

        if VERSION_COMMENT_PATTERN.search(reference.line_text):
            continue

        report(
            "warning",
            f"{reference.action} is pinned to commit {reference.ref} without a "
            "trailing `# vX.Y.Z` comment; add one so Dependabot can raise "
            "version update pull requests",
            reference,
        )


def check_consistent_refs(references: list[Reference]) -> int:
    """Fail when the same action repository is referenced with mixed refs."""
    by_repo: dict[str, list[Reference]] = defaultdict(list)

    for reference in references:
        owner_repo = "/".join(reference.action.split("/")[:2])
        by_repo[owner_repo].append(reference)

    failures = 0

    for owner_repo, refs in sorted(by_repo.items()):
        distinct = {reference.ref for reference in refs}

        if len(distinct) > 1:
            rendered = ", ".join(sorted(distinct))
            for reference in refs:
                report(
                    "error",
                    f"{owner_repo} is referenced with mixed versions ({rendered}). "
                    f"This file uses {reference.ref}; pin every step of an action "
                    "to the same commit so they cannot resolve to different releases",
                    reference,
                )
                failures += 1

    return failures


def main() -> int:
    """Parse arguments and validate the workflow action references."""
    parser = argparse.ArgumentParser(
        description="Validate GitHub Actions references in the workflow files.",
    )

    parser.add_argument(
        "workflows",
        type=Path,
        nargs="*",
        default=[WORKFLOW_DIR],
        metavar="WORKFLOW",
        help=(f"Workflow files or directories to check (default: {WORKFLOW_DIR})"),
    )

    args = parser.parse_args()

    try:
        paths = resolve_paths(args.workflows)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not paths:
        print("no workflow files found", file=sys.stderr)
        return 2

    references = collect_references(paths)

    check_sha_annotations(references)

    failures = check_sha_pins(references) + check_consistent_refs(references)

    if failures:
        print(
            f"{failures} action reference problem(s) found",
            file=sys.stderr,
        )
        return 1

    print(f"{len(references)} action references use full-SHA pins")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
