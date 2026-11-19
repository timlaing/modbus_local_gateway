"""Regression tests for the legacy workflow-reference checker."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    "legacy_action_refs",
    Path(__file__).resolve().parents[2] / "scripts/check_action_refs.py",
)
assert SPEC is not None
assert SPEC.loader is not None
LEGACY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LEGACY
SPEC.loader.exec_module(LEGACY)


class LegacyReferenceTests(unittest.TestCase):
    """Actual YAML values, not punctuation or script examples, define a reference."""

    def test_flow_folded_and_quoted_references(self) -> None:
        """Valid flow mappings pass; punctuation inside a quoted value is retained."""
        sha = "a" * 40
        forms = [
            f"- {{uses: owner/action@{sha}}}",
            f'- uses: "owner/action@{sha}"',
            f"- uses: >-\n        owner/action@{sha}",
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.yml"
            for entry in forms:
                path.write_text("jobs:\n  check:\n    steps:\n    " + entry + "\n")
                references = LEGACY.collect_references([path])
                self.assertEqual(len(references), 1)
                self.assertEqual(references[0].ref, sha)
                self.assertEqual(LEGACY.check_sha_pins(references), 0)
            path.write_text(
                'jobs: {check: {steps: [{uses: "owner/action@' + sha + '}"}]}}'
            )
            self.assertEqual(LEGACY.collect_references([path])[0].ref, sha + "}")

    def test_script_examples_are_ignored_and_reusable_workflows_are_checked(
        self,
    ) -> None:
        """A run string cannot inject fake references into the validator."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.yml"
            path.write_text(
                "jobs:\n"
                "  reusable:\n"
                "    uses: owner/repo/.github/workflows/test.yml@main\n"
                "  check:\n"
                "    steps:\n"
                "      - run: |\n"
                "          echo 'uses: owner/fake@mutable'\n"
            )
            references = LEGACY.collect_references([path])
            self.assertEqual(
                [ref.action for ref in references],
                ["owner/repo/.github/workflows/test.yml"],
            )
            self.assertEqual(references[0].ref, "main")


if __name__ == "__main__":
    unittest.main()
