# Workflow validation policy

Validation remains in project-specific workflows. Each required aggregate rejects failed, cancelled or skipped dependencies. Sonar input generation runs without secrets; analysis consumes the triggering run’s artifact and trusted scanner configuration.

CodeRabbit automatic and incremental push reviews are disabled. Only after all validation checks succeed, including for Dependabot, may the coordinator or a maintainer request review. `Review passed` requires approval on the current head and must not be satisfied by merely requesting a review. Rerun the coordinator for the current SHA after resolving findings.

## Repository settings

The intended required checks are recorded in `workflow-policy.json`. Default workflow tokens must be read-only, security updates enabled, and actions SHA-pinned. Preserve existing review, conversation, force-push and deletion protections.

The `workflow_run` coordinator and scanner use the default-branch workflow. The PR introducing them cannot exercise its own privileged code. Keep the existing protection during bootstrap; activate `Review passed` only after the workflow is on main and a hosted run has produced it. Do not bypass failed analysis or reviews.

## Bootstrap and recovery

After the Analysis inputs workflow passes on this PR, dispatch the Sonar workflow on the PR branch with `source_run_id` set to that successful run. It verifies the source workflow, result, revision and current PR before scanning. Dispatch `coderabbit-after-checks.yml` on the PR branch with its current head `revision`; the coordinator loads policy from its own workflow revision. This tests the privileged flow before the first merge without disabling protection.

## Apply the matching repository policy

After merging, run `python3 .github/scripts/apply-workflow-policy.py` to inspect the exact ruleset change, then run it with `--apply`. The script refuses to apply an unmerged policy, preserves unrelated rules and bypass actors, binds checks to GitHub Actions, enables SHA enforcement and the replacement automation, and verifies the result. Repository settings shared with the existing workflows can be corrected before merge; new check names and action enforcement must wait for their producing workflows.

## Explicit review requester

For unattended explicit CodeRabbit requests, configure `REVIEW_REQUEST_TOKEN` as a dedicated maintainer-owned fine-grained token with Issues write, Pull requests read and Metadata read, limited to this repository. The trusted metadata-only coordinator uses that client only to identify the requester and post the fixed review command. Its normal GitHub Actions client retains check/status duties and has no PR/issue write permission. The workflow does not check out repository code. Request markers are deduplicated per authenticated requester and revision.

Without the secret, automatic reviews are disabled to preserve validation ordering; a maintainer must request review after checks pass. The gate never treats a missing request credential as approval. Rotate the token before expiry.

The migration accepts only an explicit main-only ruleset; shared or wildcard branch targets require a separate main policy. Review event notifications contain no checkout or credentials and trigger trusted re-evaluation of readiness and revoked approvals. Polling is bounded to 45 one-minute attempts.

Review command markers are deduplicated per requester, revision and run attempt. A requester may post at most three requests for one revision. Once exhausted, a maintainer requests review manually; after current-head CodeRabbit approval arrives, rerunning the coordinator can pass. A new revision resets the count.

The required `Review notifier policy` commit status is written by a checkout-free `pull_request_target` worker from the default branch. It checks the complete notification structure, regular Git file modes, and the trusted enforcement/receiver files as data. Pinned action updates must belong to the official action repository. Changes to security-policy logic need a maintainer-reviewed trusted baseline update; the PR cannot rewrite its own automatic validator. The coordinator requires the actual status, so a same-named PR check cannot replace it.
