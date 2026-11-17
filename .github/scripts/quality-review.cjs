/** Trusted metadata-only coordination. Never execute the pull request checkout. */
const reviewBot = "coderabbitai[bot]";
function approved(reviews, sha) {
  const latest = reviews.findLast(
    (review) =>
      review.user?.login === reviewBot &&
      review.commit_id === sha &&
      review.state !== "COMMENTED",
  );
  return latest?.state === "APPROVED";
}
function readiness(required, checks, statuses) {
  const passed = new Set();
  for (const name of required) {
    const check = checks
      .filter(
        (item) => item.name === name && item.app?.slug === "github-actions",
      )
      .sort((left, right) => right.id - left.id)[0];
    if (check) {
      if (check.status === "completed" && check.conclusion === "success")
        passed.add(name);
      continue;
    }
    const status = statuses
      .filter(
        (item) =>
          item.context === name &&
          item.creator?.login === "github-actions[bot]",
      )
      .sort((left, right) => right.id - left.id)[0];
    if (status?.state === "success") passed.add(name);
  }
  return required.filter((name) => !passed.has(name));
}
async function currentPull(github, context) {
  const upstream = context.payload.workflow_run;
  if (upstream && !["push", "pull_request"].includes(upstream.event)) return;
  const sha = upstream?.head_sha || process.env.REVISION;
  if (!/^[0-9a-f]{40}$/.test(sha || ""))
    throw new Error("A full triggering revision is required");
  const pulls = await github.paginate(
    github.rest.repos.listPullRequestsAssociatedWithCommit,
    { ...context.repo, commit_sha: sha, per_page: 100 },
  );
  const fullName = `${context.repo.owner}/${context.repo.repo}`;
  const matches = pulls.filter(
    (pull) =>
      pull.state === "open" &&
      !pull.draft &&
      pull.base.repo.full_name === fullName &&
      pull.base.ref === "main" &&
      (pull.head.sha === sha || pull.merge_commit_sha === sha),
  );
  if (matches.length > 1)
    throw new Error("Trigger does not identify a unique current PR");
  return matches[0];
}
async function validation(github, context, pull, required) {
  const { data: current } = await github.rest.pulls.get({
    ...context.repo,
    pull_number: pull.number,
  });
  if (
    current.state !== "open" ||
    current.draft ||
    current.head.sha !== pull.head.sha
  )
    throw new Error("PR revision changed; validate the new revision");
  // PR checks can attach to the current merge revision or head. Analysis statuses use the head.
  const refs = [
    ...new Set([current.merge_commit_sha, current.head.sha].filter(Boolean)),
  ];
  const checks = (
    await Promise.all(
      refs.map((ref) =>
        github.paginate(github.rest.checks.listForRef, {
          ...context.repo,
          ref,
          filter: "latest",
          per_page: 100,
        }),
      ),
    )
  ).flat();
  const statuses = await github.paginate(
    github.rest.repos.listCommitStatusesForRef,
    { ...context.repo, ref: pull.head.sha, per_page: 100 },
  );
  return readiness(required, checks, statuses);
}
async function requestReview(github, context, pull) {
  const prefix = `<!-- quality-review:${pull.head.sha}:`;
  const marker = `${prefix}${context.runId}:${process.env.GITHUB_RUN_ATTEMPT || "1"} -->`;
  const comments = await github.paginate(github.rest.issues.listComments, {
    ...context.repo,
    issue_number: pull.number,
    per_page: 100,
  });
  const requests = comments.filter(
    (comment) =>
      comment.user?.login === "github-actions[bot]" &&
      comment.body?.includes(prefix),
  );
  if (requests.some((comment) => comment.body.includes(marker))) return;
  if (requests.length >= 3)
    throw new Error(
      "Three review requests failed for this revision; request review manually",
    );
  await github.rest.issues.createComment({
    ...context.repo,
    issue_number: pull.number,
    body: `@coderabbitai review\n\n${marker}`,
  });
}
async function checkApproval(github, context, core, pull, required) {
  const missing = await validation(github, context, pull, required);
  if (missing.length) {
    core.info(`PR ${pull.number}: waiting for ${missing.join(", ")}`);
    return false;
  }
  const reviews = await github.paginate(github.rest.pulls.listReviews, {
    ...context.repo,
    pull_number: pull.number,
    per_page: 100,
  });
  if (approved(reviews, pull.head.sha)) return true;
  await requestReview(github, context, pull);
  core.info(
    `PR ${pull.number}: waiting for CodeRabbit approval of ${pull.head.sha}`,
  );
  return false;
}
async function poll(check, sleep, remaining) {
  if (remaining <= 0)
    throw new Error(
      "Validation or review incomplete; rerun this workflow after resolving the checks",
    );
  if (await check()) return;
  await sleep(20000);
  return poll(check, sleep, remaining - 1);
}
async function run({
  github,
  context,
  core,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  attempts = 150,
}) {
  const pull = await currentPull(github, context);
  if (!pull) {
    core.info("No current open PR for this revision");
    return;
  }
  const required = JSON.parse(process.env.REQUIRED_CHECKS || "[]");
  if (!required.length) throw new Error("Required validation policy is empty");
  const status = (state, description) =>
    github.rest.repos.createCommitStatus({
      ...context.repo,
      sha: pull.head.sha,
      context: "Review passed",
      state,
      description,
      target_url: `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`,
    });
  await status(
    "pending",
    "Waiting for validation and current-commit CodeRabbit approval",
  );
  try {
    await poll(
      () => checkApproval(github, context, core, pull, required),
      sleep,
      attempts,
    );
    await status(
      "success",
      "Validation and current-commit CodeRabbit approval passed",
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
