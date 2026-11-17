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
  const missing = new Set(required.filter((name) => !passed.has(name)));
  // Review jobs and their own status must not wait on themselves. Every other
  // reported check must finish successfully (conditionally skipped jobs are OK).
  const reviewNames = new Set([
    "CodeRabbit",
    "Review passed",
    "CodeRabbit after checks",
  ]);
  const latestChecks = new Map();
  for (const check of [...checks].sort((left, right) => left.id - right.id))
    latestChecks.set(check.name, check);
  for (const [name, check] of latestChecks) {
    if (reviewNames.has(name)) continue;
    if (
      check.status !== "completed" ||
      !["success", "skipped"].includes(check.conclusion)
    )
      missing.add(name);
  }
  const latestStatuses = new Map();
  for (const status of [...statuses].sort((left, right) => left.id - right.id))
    latestStatuses.set(status.context, status);
  for (const [name, status] of latestStatuses)
    if (!reviewNames.has(name) && status.state !== "success") missing.add(name);
  return [...missing];
}
function mergeChecks(merge, head) {
  const names = new Set(merge.map((check) => check.name));
  return [...merge, ...head.filter((check) => !names.has(check.name))];
}
async function currentPull(github, context) {
  const upstream = context.payload.workflow_run;
  if (
    upstream &&
    !["push", "pull_request", "pull_request_review"].includes(upstream.event)
  )
    return;
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
  const groups = await Promise.all(
    refs.map((ref) =>
      github.paginate(github.rest.checks.listForRef, {
        ...context.repo,
        ref,
        filter: "latest",
        per_page: 100,
      }),
    ),
  );
  const checks = mergeChecks(groups[0], groups[1] || []);
  const statuses = await github.paginate(
    github.rest.repos.listCommitStatusesForRef,
    { ...context.repo, ref: pull.head.sha, per_page: 100 },
  );
  return readiness(required, checks, statuses);
}
async function requestReview(github, context, pull, request) {
  if (request.sent) return;
  if (!request.login) {
    const { data } = await request.client.rest.users.getAuthenticated();
    request.login = data.login;
  }
  const prefix = `<!-- quality-review:${pull.head.sha}:`;
  const marker = `${prefix}${context.runId}:${process.env.GITHUB_RUN_ATTEMPT || "1"} -->`;
  const comments = await github.paginate(github.rest.issues.listComments, {
    ...context.repo,
    issue_number: pull.number,
    per_page: 100,
  });
  const requests = comments.filter(
    (comment) =>
      comment.user?.login === request.login && comment.body?.includes(prefix),
  );
  if (requests.some((comment) => comment.body.includes(marker))) return;
  if (requests.length >= 3)
    throw new Error(
      "Three review requests failed for this revision; request review manually",
    );
  await request.client.rest.issues.createComment({
    ...context.repo,
    issue_number: pull.number,
    body: `@coderabbitai review\n\n${marker}`,
  });
  request.sent = true;
}
async function checkApproval(github, context, core, pull, required, request) {
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
  if (request.client) await requestReview(github, context, pull, request);
  else
    core.info(
      "Configure REVIEW_REQUEST_TOKEN or request a maintainer review manually",
    );
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
  await sleep(60000);
  return poll(check, sleep, remaining - 1);
}
async function run({
  github,
  context,
  core,
  sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
  attempts = 45,
  reviewClient = null,
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
  const request = {
    client: reviewClient,
    login: reviewClient === github ? "github-actions[bot]" : null,
  };
  try {
    await poll(
      () => checkApproval(github, context, core, pull, required, request),
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
module.exports = { approved, readiness, mergeChecks, run };
