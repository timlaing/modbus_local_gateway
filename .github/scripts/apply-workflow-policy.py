"""Apply the reviewed workflow policy only after it exists on the default branch."""

from __future__ import annotations

import argparse
import base64
from fnmatch import fnmatchcase
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

REPOSITORY = "timlaing/modbus_local_gateway"
POLICY_PATH = ".github/workflow-policy.json"
ACTIONS_PERMISSIONS = "actions/permissions"


def api(path: str, method: str = "GET", body: dict[str, Any] | None = None) -> Any:
    """Call the installed GitHub CLI without exposing authentication values."""
    executable = shutil.which("gh")
    if executable is None:
        raise SystemExit("Install and authenticate GitHub CLI first")
    command = [
        executable,
        "api",
        "--method",
        method,
        f"repos/{REPOSITORY}" + (f"/{path}" if path else ""),
    ]
    if body is not None:
        command += ["--input", "-"]
    result = subprocess.run(  # noqa: S603
        command,
        input=json.dumps(body) if body is not None else None,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout) if result.stdout.strip() else None


def applies_to_main(detail: dict[str, Any]) -> bool:
    """Honor exclusions before selecting a supported main-branch ruleset."""
    refs = detail.get("conditions", {}).get("ref_name", {})
    aliases = ["refs/heads/main", "~DEFAULT_BRANCH", "~ALL"]
    included = any(pattern in aliases for pattern in refs.get("include", []))
    excluded = any(
        pattern in aliases or fnmatchcase("refs/heads/main", pattern)
        for pattern in refs.get("exclude", [])
    )
    return detail["target"] == "branch" and included and not excluded


def main_ruleset() -> dict[str, Any]:
    """Find the active main policy while preserving all unrelated protections."""
    candidates = api("rulesets?includes_parents=true")
    rulesets = []
    for candidate in candidates:
        if (
            candidate["source_type"] != "Repository"
            or candidate["enforcement"] != "active"
        ):
            continue
        detail = api(f"rulesets/{candidate['id']}")
        if applies_to_main(detail):
            rulesets.append(detail)
    if not rulesets:
        raise SystemExit("No active main-branch ruleset; review protection manually")
    return next(
        (
            item
            for item in rulesets
            if any(rule["type"] == "required_status_checks" for rule in item["rules"])
        ),
        rulesets[0],
    )


def main() -> None:
    """Plan changes, or apply them after verifying the policy on main."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    policy = json.loads(Path(POLICY_PATH).read_text(encoding="utf-8"))
    if args.apply:
        remote = api(f"contents/{POLICY_PATH}?ref=main")
        deployed = json.loads(base64.b64decode(remote["content"]))
        if deployed != policy:
            raise SystemExit("The reviewed policy must be merged into main first")
    selected = main_ruleset()
    payload = {
        key: selected[key]
        for key in [
            "name",
            "target",
            "enforcement",
            "conditions",
            "bypass_actors",
            "rules",
        ]
        if key in selected
    }
    rule = next(
        (item for item in payload["rules"] if item["type"] == "required_status_checks"),
        None,
    )
    if rule is None:
        rule = {"type": "required_status_checks", "parameters": {}}
        payload["rules"].append(rule)
    rule["parameters"] = {
        "strict_required_status_checks_policy": True,
        "do_not_enforce_on_create": False,
        "required_status_checks": [
            {"context": name, "integration_id": 15368}
            for name in policy["required_checks"]
        ],
    }
    print(
        json.dumps(
            {
                "repository": REPOSITORY,
                "ruleset_id": selected["id"],
                "payload": payload,
            },
            indent=2,
        )
    )
    if not args.apply:
        return
    api(f"rulesets/{selected['id']}", "PUT", payload)
    current = api(ACTIONS_PERMISSIONS)
    api(
        ACTIONS_PERMISSIONS,
        "PUT",
        {
            "enabled": current["enabled"],
            "allowed_actions": current["allowed_actions"],
            "sha_pinning_required": True,
        },
    )
    api(
        "actions/permissions/workflow",
        "PUT",
        {
            "default_workflow_permissions": "read",
            "can_approve_pull_request_reviews": True,
        },
    )
    api(
        "",
        "PATCH",
        {
            "allow_auto_merge": True,
            "delete_branch_on_merge": True,
            "allow_update_branch": True,
        },
    )
    api("automated-security-fixes", "PUT")
    for workflow in ["coderabbit-after-checks.yml", "dependabot-auto-merge.yml"]:
        api(f"actions/workflows/{workflow}/enable", "PUT")
    actual = api(f"rulesets/{selected['id']}")
    actual_checks = next(
        item for item in actual["rules"] if item["type"] == "required_status_checks"
    )
    if actual_checks != rule:
        raise SystemExit("Required checks did not match after update")
    if not api(ACTIONS_PERMISSIONS)["sha_pinning_required"]:
        raise SystemExit("SHA enforcement did not activate")
    print("Workflow policy applied and required checks verified")


if __name__ == "__main__":
    main()
