/** Trusted metadata-only coordination. Never execute the pull request checkout. */
const reviewBot = "coderabbitai[bot]";
function approved(reviews, sha) {
  const latest = reviews
    .filter(
      (r) =>
        r.user?.login === reviewBot &&
        r.commit_id === sha &&
        r.state !== "COMMENTED",
    )
    .at(-1);
  return latest?.state === "APPROVED";
}
function readiness(required, checks, statuses) {
  const passed = new Set();
  for (const name of required) {
    const matches = checks
      .filter((c) => c.name === name && c.app?.slug === "github-actions")
      .sort((a, b) => b.id - a.id);
    if (matches.length) {
      if (
        matches[0].status === "completed" &&
        matches[0].conclusion === "success"
      )
        passed.add(name);
      continue;
    }
    const status = statuses
      .filter(
        (s) => s.context === name && s.creator?.login === "github-actions[bot]",
      )
      .sort((a, b) => b.id - a.id)[0];
    if (status?.state === "success") passed.add(name);
  }
  return required.filter((name) => !passed.has(name));
}
async function run({
  github,
  context,
  core,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  attempts = 150,
}) {
  const { owner, repo } = context.repo;
  const upstream = context.payload.workflow_run;
  if (upstream && !["push", "pull_request"].includes(upstream.event)) return;
  const sha = upstream?.head_sha || process.env.REVISION;
  if (!/^[0-9a-f]{40}$/.test(sha || ""))
    throw new Error("A full triggering revision is required");
  const pulls = await github.paginate(
    github.rest.repos.listPullRequestsAssociatedWithCommit,
    { owner, repo, commit_sha: sha, per_page: 100 },
  );
  const matches = pulls.filter(
    (p) =>
      p.state === "open" &&
      !p.draft &&
      p.base.repo.full_name === `${owner}/${repo}` &&
      p.base.ref === "main" &&
      (p.head.sha === sha || p.merge_commit_sha === sha),
  );
  if (matches.length === 0) {
    core.info("No current open PR for this revision");
    return;
  }
  if (matches.length !== 1)
    throw new Error("Trigger does not identify a unique current PR");
  const pr = matches[0];
  const required = JSON.parse(process.env.REQUIRED_CHECKS || "[]");
  if (!required.length) throw new Error("Required validation policy is empty");
  const status = (state, description) =>
    github.rest.repos.createCommitStatus({
      owner,
      repo,
      sha: pr.head.sha,
      context: "Review passed",
      state,
      description,
      target_url: `${context.serverUrl}/${owner}/${repo}/actions/runs/${context.runId}`,
    });
  await status(
    "pending",
    "Waiting for validation and current-commit CodeRabbit approval",
  );
  const prefix = `<!-- quality-review:${pr.head.sha}:`;
  const marker = `${prefix}${context.runId}:${process.env.GITHUB_RUN_ATTEMPT || "1"} -->`;
  try {
    for (let i = 0; i < attempts; i++) {
      const { data: current } = await github.rest.pulls.get({
        owner,
        repo,
        pull_number: pr.number,
      });
      if (
        current.state !== "open" ||
        current.draft ||
        current.head.sha !== pr.head.sha
      )
        throw new Error("PR revision changed; validate the new revision");
      // Required PR checks are produced on the merge revision. Head statuses are
      // used only for trusted downstream analysis tied to the triggering head.
      const refs = [
        ...new Set(
          [current.merge_commit_sha, current.head.sha].filter(Boolean),
        ),
      ];
      const checks = (
        await Promise.all(
          refs.map((ref) =>
            github.paginate(github.rest.checks.listForRef, {
              owner,
              repo,
              ref,
              filter: "latest",
              per_page: 100,
            }),
          ),
        )
      ).flat();
      const statuses = await github.paginate(
        github.rest.repos.listCommitStatusesForRef,
        { owner, repo, ref: pr.head.sha, per_page: 100 },
      );
      const missing = readiness(required, checks, statuses);
      if (missing.length === 0) {
        const reviews = await github.paginate(github.rest.pulls.listReviews, {
          owner,
          repo,
          pull_number: pr.number,
          per_page: 100,
        });
        if (approved(reviews, pr.head.sha)) {
          await status(
            "success",
            "Validation and current-commit CodeRabbit approval passed",
          );
          return;
        }
        const comments = await github.paginate(
          github.rest.issues.listComments,
          { owner, repo, issue_number: pr.number, per_page: 100 },
        );
        if (
          !comments.some(
            (c) =>
              c.user?.login === "github-actions[bot]" &&
              c.body?.includes(marker),
          )
        ) {
          const prior = comments.filter(
            (c) =>
              c.user?.login === "github-actions[bot]" &&
              c.body?.includes(prefix),
          );
          if (prior.length >= 3)
            throw new Error(
              "Three review requests failed for this revision; request review manually",
            );
          await github.rest.issues.createComment({
            owner,
            repo,
            issue_number: pr.number,
            body: `@coderabbitai review\n\n${marker}`,
          });
        }
        core.info(
          `PR ${pr.number}: waiting for CodeRabbit approval of ${pr.head.sha}`,
        );
      } else core.info(`PR ${pr.number}: waiting for ${missing.join(", ")}`);
      await sleep(20000);
    }
    throw new Error(
      "Validation or review incomplete; rerun this workflow after resolving the checks",
    );
  } catch (error) {
    await status(
      "failure",
      "Validation or review incomplete; inspect this run and rerun after resolution",
    );
    throw error;
  }
}
module.exports = { approved, readiness, run };
