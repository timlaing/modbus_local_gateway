# Reviews and dependency auto-merge

CodeRabbit automatic and incremental push reviews are disabled. The metadata-only **CodeRabbit after checks** coordinator waits for the validation checks in `workflow-policy.json` and every other reported check before requesting review. Conditional skipped jobs are allowed only when they are not required checks.

`Review passed` requires CodeRabbit approval of the exact current head. A request, a successful CodeRabbit check, an old approval, or an approval from another account cannot satisfy this gate. Review event notifications re-evaluate readiness and withdrawn approval through the trusted coordinator. Merge-commit results take precedence over matching head-only reruns.

The coordinator never checks out PR code or submits a GitHub Actions approval. Its normal token reads metadata and writes the gate status. An optional dedicated requester credential can post review commands; without it a maintainer requests review after validation succeeds. See [the workflow policy](WORKFLOW_POLICY.md) for setup and recovery.

## Dependabot

Only same-repository patch/minor Dependabot updates targeting main qualify for native auto-merge. The workflow verifies that the intended required checks are enforced before enabling auto-merge. GitHub still requires checks and reviews to pass, and expected-head checks protect against revision changes. Already-mergeable updates use the native merge API under the same protection.

Dependabot remains subject to the same CodeRabbit approval gate. The workflow never creates an approval, checks out PR code, or bypasses branch protection. Repository-wide workflow approval permission is preserved by the settings migration.
