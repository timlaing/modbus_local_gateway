# Workflow validation policy

Validation remains in project-specific workflows. Each required aggregate rejects failed, cancelled or skipped dependencies. Sonar input generation runs without secrets; analysis consumes the triggering run’s artifact and trusted scanner configuration.

CodeRabbit may review automatically on open or push where the service permits it. After validation succeeds, including for Dependabot, the coordinator explicitly requests any missing review. `Review passed` requires approval on the current head and must not be satisfied by merely requesting a review. Rerun the coordinator for the current SHA after resolving findings.

## Repository settings

The intended required checks are recorded in `workflow-policy.json`. Default workflow tokens must be read-only, security updates enabled, and actions SHA-pinned. Preserve existing review, conversation, force-push and deletion protections.

The `workflow_run` coordinator and scanner use the default-branch workflow. The PR introducing them cannot exercise its own privileged code. Keep the existing protection during bootstrap; activate `Review passed` only after the workflow is on main and a hosted run has produced it. Do not bypass failed analysis or reviews.

## Bootstrap and recovery

After the analysis-input or test workflow passes on this PR, dispatch the Sonar workflow on the PR branch with `source_run_id` set to that successful run. It verifies the source workflow, result, revision and current PR before scanning. Dispatch `coderabbit-after-checks.yml` on the PR branch with its current head `revision`; the coordinator loads policy from its own workflow revision. This tests the privileged flow before the first merge without disabling protection.

## Apply the matching repository policy

After merging, run `python3 .github/scripts/apply-workflow-policy.py` to inspect the exact ruleset change, then run it with `--apply`. The script refuses to apply an unmerged policy, preserves unrelated rules and bypass actors, binds checks to GitHub Actions, enables SHA enforcement and the replacement automation, and verifies the result. Repository settings shared with the existing workflows can be corrected before merge; new check names and action enforcement must wait for their producing workflows.
