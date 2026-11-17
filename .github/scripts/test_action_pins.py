"""Action pinning must validate complete YAML values rather than text prefixes."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import action_pins
from action_pins import invalid_references
import yaml


class ActionPinTests(unittest.TestCase):
    """Exercise YAML forms that line-based checks can accidentally overlook."""

    def test_reviews_wait_for_validation(self) -> None:
        """Push-triggered reviews must not race validation-gated requests."""
        config = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / ".coderabbit.yaml").read_text(),
        )
        automatic = config["reviews"]["auto_review"]
        self.assertIs(automatic["enabled"], False)
        self.assertIs(automatic["auto_incremental_review"], False)
        self.assertEqual(automatic["description_keyword"], "")

    def test_yaml_forms_preserve_the_complete_reference(self) -> None:
        """Quoted keys, folded values and flow mappings are all inspected."""
        sha = "a" * 40
        for entry in [
            f'      - "uses": owner/action@{sha}',
            f"      - 'uses': 'owner/action@{sha}'",
            f"      - uses: >-\n          owner/action@{sha}",
            f"      - {{uses: owner/action@{sha}}}",
        ]:
            document = yaml.safe_load("jobs:\n  check:\n    steps:\n" + entry)
            self.assertEqual(invalid_references(document), [])
            mutated = yaml.safe_load(
                "jobs:\n  check:\n    steps:\n" + entry.replace(sha, sha + "!"),
            )
            self.assertEqual(invalid_references(mutated), ["owner/action@" + sha + "!"])

    def test_empty_workflow_directory_is_an_error(self) -> None:
        """An empty scan cannot report that immutable references were validated."""
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(action_pins, "WORKFLOW_DIR", Path(directory)),
            self.assertRaisesRegex(SystemExit, "No workflow files"),
        ):
            action_pins.main()

    def test_examples_in_scripts_are_not_action_invocations(self) -> None:
        """A quoted mutable reference in a script does not become a false positive."""
        document = {
            "jobs": {"check": {"steps": [{"run": "echo 'uses: owner/example@main'"}]}}
        }
        self.assertEqual(invalid_references(document), [])

    def test_tags_and_branches_fail_but_local_workflows_are_allowed(self) -> None:
        """Both job-level reusable workflows and step actions are validated."""
        document = {
            "jobs": {
                "local": {"uses": "./.github/workflows/tests.yml"},
                "remote": {"uses": "owner/repo/.github/workflows/tests.yml@main"},
                "steps": {"steps": [{"uses": "actions/checkout@v7"}]},
            }
        }
        self.assertEqual(
            invalid_references(document),
            [
                "owner/repo/.github/workflows/tests.yml@main",
                "actions/checkout@v7",
            ],
        )

    def test_workflow_files_are_parsed_and_invalid_pins_fail(self) -> None:
        """Validate actual files, including a failing action in a later workflow."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "valid.yml").write_text("jobs: {local: {uses: './local.yml'}}")
            with patch.object(action_pins, "WORKFLOW_DIR", root):
                action_pins.main()
                (root / "bad.yml").write_text(
                    "jobs: {bad: {uses: 'owner/action@main'}}"
                )
                with self.assertRaisesRegex(SystemExit, "Unpinned references"):
                    action_pins.main()


class WorkflowSourceTests(unittest.TestCase):
    """The metadata-only workflow must execute exactly the tested coordinator."""

    def test_embedded_coordinator_matches_tested_source(self) -> None:
        """Prevent divergence without a privileged repository checkout."""
        root = Path(__file__).resolve().parents[1]
        workflow = yaml.safe_load(
            (root / "workflows/coderabbit-after-checks.yml").read_text()
        )
        steps = workflow["jobs"]["review"]["steps"]
        self.assertEqual(len(steps), 1)
        source = (root / "scripts/quality-review.cjs").read_text()
        expected = source.rsplit("module.exports = ", 1)[0] + (
            "const reviewClient = process.env.REVIEW_REQUEST_TOKEN\n"
            "  ? new github.constructor({ auth: "
            "process.env.REVIEW_REQUEST_TOKEN })\n"
            "  : null;\n"
            "await run({ github, context, core, reviewClient });\n"
        )
        self.assertEqual(steps[0]["with"]["script"], expected)

    def test_sonar_settings_have_unique_keys_and_disjoint_test_roots(self) -> None:
        """Avoid duplicate indexing and host paths passed to container scanners."""
        root = Path(__file__).resolve().parents[1] / "workflows"
        for path in root.glob("sonar*.y*ml"):
            document = yaml.safe_load(path.read_text())
            job = document.get("jobs", {}).get("analysis", {})
            for step in job.get("steps", []):
                settings = step.get("env", {}).get("SCANNER_SETTINGS")
                if settings is None:
                    continue
                entries = [
                    line.split("=", 1) for line in settings.splitlines() if "=" in line
                ]
                properties = dict(entries)
                self.assertEqual(len(properties), len(entries), str(path))
                roots = properties.get("sonar.tests", "").split(",")
                self.assertFalse(
                    any(
                        parent != child
                        and (
                            parent == "." or child.startswith(parent.rstrip("/") + "/")
                        )
                        for parent in roots
                        for child in roots
                    ),
                    str(path),
                )
                if job.get("container"):
                    self.assertNotIn("${{ runner.temp }}", settings)


if __name__ == "__main__":
    unittest.main()
