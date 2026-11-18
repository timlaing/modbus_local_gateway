/** Verify the actual validator run; the shared Actions bot identity is insufficient. */
async function notifierProof(github, context, pull, statuses) {
  const status = statuses
    .filter(
      (item) =>
        item.context === "Review notifier policy" &&
        item.creator?.login === "github-actions[bot]",
    )
    .sort((left, right) => right.id - left.id)[0];
  if (status?.state !== "success") return false;
  const prefix = `${context.serverUrl || "https://github.com"}/${context.repo.owner}/${context.repo.repo}/actions/runs/`;
  if (!status.target_url?.startsWith(prefix)) return false;
  const runId = status.target_url.slice(prefix.length);
  if (!/^[1-9][0-9]*$/.test(runId)) return false;
  const [{ data: run }, { data: workflow }, { data: repository }] =
    await Promise.all([
      github.rest.actions.getWorkflowRun({ ...context.repo, run_id: runId }),
      github.rest.actions.getWorkflow({
        ...context.repo,
        workflow_id: "review-notifier-policy.yml",
      }),
      github.rest.repos.get({ ...context.repo }),
    ]);
  if (
    run.workflow_id !== workflow.id ||
    workflow.path !== ".github/workflows/review-notifier-policy.yml" ||
    run.status !== "completed" ||
    run.conclusion !== "success" ||
    run.display_title !== `Review notifier policy / ${pull.head.sha}`
  )
    return false;
  if (run.event === "pull_request_target") return true;
  if (run.event !== "workflow_dispatch") return false;
  if (run.head_branch === repository.default_branch) return true;
  // Explicit owner-reviewed bootstrap/recovery: writer access alone never authorizes this.
  return (
    run.actor?.login === context.repo.owner && run.head_sha === pull.head.sha
  );
}
/** Trusted metadata-only coordination. Never execute the pull request checkout. */
const reviewBot = "coderabbitai[bot]";
const checkKey = (check) =>
  `${check.app?.id ?? check.app?.slug ?? "unknown"}:${check.name}`;
const statusKey = (status) =>
  `${status.creator?.id ?? status.creator?.login ?? "unknown"}:${status.context}`;
function approved(reviews, sha) {
  const latest = reviews.findLast(
    (review) =>
      review.user?.login === reviewBot &&
      review.commit_id === sha &&
      review.state !== "COMMENTED",
  );
  return latest?.state === "APPROVED";
}
function requiredPassed(name, checks, statuses) {
  const statusPassed = () =>
    statuses
      .filter(
        (item) =>
          item.context === name &&
          item.creator?.login === "github-actions[bot]",
      )
      .sort((left, right) => right.id - left.id)[0]?.state === "success";
  if (name === "Review notifier policy") return statusPassed();
  const check = checks
    .filter((item) => item.name === name && item.app?.slug === "github-actions")
    .sort((left, right) => right.id - left.id)[0];
  if (check)
    return check.status === "completed" && check.conclusion === "success";
  return statusPassed();
}
function readiness(required, checks, statuses) {
  return [
    ...new Set([
      ...required.filter((name) => !requiredPassed(name, checks, statuses)),
      ...unsuccessfulChecks(checks, statuses),
    ]),
  ];
}
function reviewCheck(check) {
  const producer = {
    CodeRabbit: "coderabbitai",
    "CodeRabbit after checks": "github-actions",
  }[check.name];
  return producer !== undefined && check.app?.slug === producer;
}
function reviewStatus(status) {
  return (
    status.context === "Review passed" &&
    status.creator?.login === "github-actions[bot]"
  );
}
function unsuccessfulChecks(checks, statuses) {
  const missing = new Set();
  // Review jobs and their own status must not wait on themselves. Every other
  // reported check must finish successfully (conditionally skipped jobs are OK).
  const latestChecks = new Map();
  for (const check of [...checks].sort((left, right) => left.id - right.id))
    latestChecks.set(checkKey(check), check);
  for (const check of latestChecks.values()) {
    const name = check.name;
    if (reviewCheck(check)) continue;
    if (
      check.status !== "completed" ||
      !["success", "skipped"].includes(check.conclusion)
    )
      missing.add(name);
  }
  const latestStatuses = new Map();
  for (const status of [...statuses].sort((left, right) => left.id - right.id))
    latestStatuses.set(statusKey(status), status);
  for (const status of latestStatuses.values())
    if (!reviewStatus(status) && status.state !== "success")
      missing.add(status.context);
  return [...missing];
}
function mergeChecks(merge, head) {
  const names = new Set(merge.map(checkKey));
  return [...merge, ...head.filter((check) => !names.has(checkKey(check)))];
}
function eligiblePull(pull, fullName) {
  return (
    pull.state === "open" &&
    !pull.draft &&
    pull.base.ref === "main" &&
    pull.base.repo.full_name === fullName
  );
}
async function ensureUniqueHead(github, context, pull) {
  const associated = await github.paginate(
    github.rest.repos.listPullRequestsAssociatedWithCommit,
    { ...context.repo, commit_sha: pull.head.sha, per_page: 100 },
  );
  const matches = associated.filter(
    (item) =>
      eligiblePull(item, context.repo.owner + "/" + context.repo.repo) &&
      item.head.sha === pull.head.sha,
  );
  if (matches.length !== 1 || matches[0].number !== pull.number) {
    await github.rest.repos.createCommitStatus({
      ...context.repo,
      sha: pull.head.sha,
      context: "Review passed",
      state: "failure",
      description: "Ambiguous PR head; use a unique revision per PR",
    });
    throw new Error("Expected one eligible PR for this head");
  }
}
async function eventPull(github, context) {
  const expected = context.payload.pull_request;
  const { data: current } = await github.rest.pulls.get({
    ...context.repo,
    pull_number: expected.number,
  });
  if (
    current.head.sha !== expected.head.sha ||
    !eligiblePull(current, context.repo.owner + "/" + context.repo.repo)
  )
    return;
  await ensureUniqueHead(github, context, current);
  return current;
}
async function currentPull(github, context) {
  if (context.eventName === "pull_request_target")
    return eventPull(github, context);
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
      eligiblePull(pull, fullName) &&
      (pull.head.sha === sha || pull.merge_commit_sha === sha),
  );
  if (matches.length > 1) await ensureUniqueHead(github, context, matches[0]);
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
    !eligiblePull(current, `${context.repo.owner}/${context.repo.repo}`) ||
    current.head.sha !== pull.head.sha
  )
    throw new Error("PR revision changed; validate the new revision");
  await ensureUniqueHead(github, context, current);
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
  const statusGroups = await Promise.all(
    refs.map((ref) =>
      github.paginate(github.rest.repos.listCommitStatusesForRef, {
        ...context.repo,
        ref,
        per_page: 100,
      }),
    ),
  );
  const headStatuses = statusGroups[refs.indexOf(current.head.sha)];
  const mergeStatusNames = new Set(statusGroups[0].map(statusKey));
  const combined = [
    ...statusGroups[0],
    ...(statusGroups[1] || []).filter(
      (item) => !mergeStatusNames.has(statusKey(item)),
    ),
  ];
  const statuses = [
    ...combined.filter((item) => item.context !== "Review notifier policy"),
    ...headStatuses.filter((item) => item.context === "Review notifier policy"),
  ];
  const missing = readiness(required, checks, statuses);
  if (
    required.includes("Review notifier policy") &&
    !(await notifierProof(github, context, pull, headStatuses))
  )
    missing.push("Review notifier policy provenance");
  return { missing: [...new Set(missing)], merge: current.merge_commit_sha };
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
  const { missing, merge } = await validation(github, context, pull, required);
  if (missing.length) {
    core.info(`PR ${pull.number}: waiting for ${missing.join(", ")}`);
    return false;
  }
  const reviews = await github.paginate(github.rest.pulls.listReviews, {
    ...context.repo,
    pull_number: pull.number,
    per_page: 100,
  });
  const { data: final } = await github.rest.pulls.get({
    ...context.repo,
    pull_number: pull.number,
  });
  if (
    !eligiblePull(final, `${context.repo.owner}/${context.repo.repo}`) ||
    final.head.sha !== pull.head.sha
  )
    throw new Error("PR revision changed during validation");
  if (final.merge_commit_sha !== merge) return false;
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
    let currentApproval = false;
    try {
      currentApproval = await checkApproval(
        github,
        context,
        core,
        pull,
        required,
        { ...request, sent: true },
      );
    } catch (recheckError) {
      core.info(`Final validation failed: ${recheckError.message}`);
    }
    if (currentApproval) {
      await status(
        "success",
        "Validation and current-commit CodeRabbit approval passed",
      );
      return;
    }
    await status(
      "failure",
      "Validation or review incomplete; inspect this run and rerun after resolution",
    );
    throw error;
  }
}
module.exports = {
  approved,
  readiness,
  mergeChecks,
  notifierProof,
  checkApproval,
  run,
};
