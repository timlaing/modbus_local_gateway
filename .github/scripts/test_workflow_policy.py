"""Regression checks for the guarded repository-settings migration."""

from __future__ import annotations

import base64
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "workflow_policy", Path(__file__).with_name("apply-workflow-policy.py")
)
assert SPEC is not None and SPEC.loader is not None
POLICY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(POLICY)


class MigrationTests(unittest.TestCase):
    """The migration must preserve protections and reject an unmerged policy."""

    def test_dry_run_preserves_unrelated_protections(self) -> None:
        """Only the required-check rule changes in the generated payload."""
        original = {
            "id": 1,
            "name": "main",
            "target": "branch",
            "enforcement": "active",
            "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
            "bypass_actors": [
                {"actor_type": "RepositoryRole", "actor_id": 5, "bypass_mode": "always"}
            ],
            "rules": [
                {"type": "deletion"},
                {"type": "non_fast_forward"},
                {
                    "type": "pull_request",
                    "parameters": {"required_approving_review_count": 1},
                },
                {
                    "type": "required_status_checks",
                    "parameters": {"required_status_checks": []},
                },
            ],
        }
        calls: list[str] = []

        def api(path: str, method: str = "GET", body: object = None) -> object:
            del body
            self.assertEqual(method, "GET")
            calls.append(path)
            if path.startswith("rulesets?"):
                return [{"id": 1, "source_type": "Repository", "enforcement": "active"}]
            return deepcopy(original)

        output = io.StringIO()
        with (
            patch.object(sys, "argv", [__file__]),
            patch.object(POLICY, "api", side_effect=api),
            patch.object(
                Path,
                "read_text",
                return_value='{"required_checks":["Validate ci","Review passed"]}',
            ),
            redirect_stdout(output),
        ):
            POLICY.main()
        payload = json.loads(output.getvalue())["payload"]
        for key in ["name", "target", "enforcement", "conditions", "bypass_actors"]:
            self.assertEqual(payload[key], original[key])
        self.assertEqual(payload["rules"][:3], original["rules"][:3])
        expected = [
            {"context": "Validate ci", "integration_id": 15368},
            {"context": "Review passed", "integration_id": 15368},
        ]
        self.assertEqual(
            payload["rules"][-1]["parameters"]["required_status_checks"], expected
        )
        self.assertEqual(len(calls), 2)

    def test_apply_rejects_a_policy_not_yet_on_main(self) -> None:
        """No write request is made when the deployed policy does not match."""
        calls: list[str] = []

        def api(path: str, method: str = "GET", body: object = None) -> object:
            del body
            self.assertEqual(method, "GET")
            calls.append(path)
            return {
                "content": base64.b64encode(b'{"required_checks":["old"]}').decode()
            }

        with (
            patch.object(sys, "argv", [__file__, "--apply"]),
            patch.object(POLICY, "api", side_effect=api),
            patch.object(
                Path, "read_text", return_value='{"required_checks":["Review passed"]}'
            ),
            self.assertRaisesRegex(SystemExit, "merged into main first"),
        ):
            POLICY.main()
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
