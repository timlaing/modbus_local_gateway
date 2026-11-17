"""Action pinning must validate complete YAML values rather than text prefixes."""

from __future__ import annotations

import unittest

from action_pins import invalid_references
import yaml


class ActionPinTests(unittest.TestCase):
    """Exercise YAML forms that line-based checks can accidentally overlook."""

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


if __name__ == "__main__":
    unittest.main()
