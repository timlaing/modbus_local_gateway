const { test } = require("node:test");
const assert = require("node:assert/strict");
const { approved, readiness, run } = require("./quality-review.cjs");
const sha = "a".repeat(40);
test("approval must be the latest CodeRabbit review on the current commit", () => {
  assert.equal(
    approved(
      [{ user: { login: "someone" }, commit_id: sha, state: "APPROVED" }],
      sha,
    ),
    false,
  );
  assert.equal(
    approved(
      [
        {
          user: { login: "coderabbitai[bot]" },
          commit_id: "b".repeat(40),
          state: "APPROVED",
        },
      ],
      sha,
    ),
    false,
  );
  const review = {
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "APPROVED",
  };
  assert.equal(approved([review], sha), true);
  assert.equal(
    approved([review, { ...review, state: "CHANGES_REQUESTED" }], sha),
    false,
  );
});
test("missing, skipped, failed and spoofed checks cannot satisfy validation", () => {
  const check = {
    id: 1,
    name: "Validate ci",
    app: { slug: "github-actions" },
    status: "completed",
    conclusion: "success",
  };
  assert.deepEqual(readiness([check.name], [check], []), []);
  for (const conclusion of ["skipped", "failure", "neutral", "cancelled"]) {
    assert.deepEqual(readiness([check.name], [{ ...check, conclusion }], []), [
      check.name,
    ]);
  }
  assert.deepEqual(
    readiness([check.name], [{ ...check, app: { slug: "other" } }], []),
    [check.name],
  );
  assert.deepEqual(
    readiness(
      [check.name],
      [check, { ...check, id: 2, conclusion: "failure" }],
      [],
    ),
    [check.name],
  );
});
test("analysis statuses must come from Actions and use the latest result", () => {
  const status = {
    id: 1,
    context: "Analysis passed",
    creator: { login: "github-actions[bot]" },
    state: "success",
  };
  assert.deepEqual(readiness([status.context], [], [status]), []);
  assert.deepEqual(
    readiness(
      [status.context],
      [],
      [{ ...status, creator: { login: "author" } }],
    ),
    [status.context],
  );
  assert.deepEqual(
    readiness(
      [status.context],
      [],
      [status, { ...status, id: 2, state: "failure" }],
    ),
    [status.context],
  );
});
test("a changed PR head fails instead of approving the previous commit", async () => {
  const states = [];
  const pr = {
    number: 1,
    state: "open",
    draft: false,
    head: { sha },
    merge_commit_sha: "b".repeat(40),
    base: { ref: "main", repo: { full_name: "owner/repo" } },
  };
  const github = {
    paginate: async () => [pr],
    rest: {
      repos: {
        listPullRequestsAssociatedWithCommit() {},
        createCommitStatus: async (v) => states.push(v.state),
      },
      pulls: {
        get: async () => ({ data: { ...pr, head: { sha: "c".repeat(40) } } }),
      },
    },
  };
  process.env.REQUIRED_CHECKS = '["Validate ci"]';
  await assert.rejects(
    run({
      github,
      context: {
        repo: { owner: "owner", repo: "repo" },
        payload: { workflow_run: { event: "pull_request", head_sha: sha } },
        serverUrl: "https://github.com",
        runId: 1,
      },
      core: { info() {} },
      attempts: 1,
    }),
    /revision changed/,
  );
  assert.deepEqual(states, ["pending", "failure"]);
});
test("review is requested only after validation, then approval completes the gate", async () => {
  const states = [],
    comments = [],
    checks = [],
    reviews = [];
  const pr = {
    number: 7,
    state: "open",
    draft: false,
    head: { sha },
    merge_commit_sha: "b".repeat(40),
    base: { ref: "main", repo: { full_name: "owner/repo" } },
  };
  const listPulls = () => {},
    listChecks = () => {},
    listStatuses = () => {},
    listReviews = () => {},
    listComments = () => {};
  const github = {
    paginate: async (method) => {
      if (method === listPulls) return [pr];
      if (method === listChecks) return checks;
      if (method === listReviews) return reviews;
      if (method === listComments) return comments;
      if (method === listStatuses) return [];
      throw new Error("Unexpected API call");
    },
    rest: {
      repos: {
        listPullRequestsAssociatedWithCommit: listPulls,
        listCommitStatusesForRef: listStatuses,
        createCommitStatus: async (v) => states.push(v.state),
      },
      checks: { listForRef: listChecks },
      pulls: { get: async () => ({ data: pr }), listReviews },
      issues: {
        listComments,
        createComment: async (v) => {
          assert.equal(checks.length, 1);
          comments.push({
            user: { login: "github-actions[bot]" },
            body: v.body,
          });
        },
      },
    },
  };
  process.env.REQUIRED_CHECKS = '["Validate ci"]';
  let tick = 0;
  await run({
    github,
    context: {
      repo: { owner: "owner", repo: "repo" },
      payload: { workflow_run: { event: "pull_request", head_sha: sha } },
      serverUrl: "https://github.com",
      runId: 1,
    },
    core: { info() {} },
    attempts: 4,
    sleep: async () => {
      tick++;
      if (tick === 1) {
        assert.equal(comments.length, 0);
        checks.push({
          id: 1,
          name: "Validate ci",
          app: { slug: "github-actions" },
          status: "completed",
          conclusion: "success",
        });
      }
      if (tick === 2)
        reviews.push({
          user: { login: "coderabbitai[bot]" },
          commit_id: sha,
          state: "APPROVED",
        });
    },
  });
  assert.deepEqual(states, ["pending", "success"]);
  assert.equal(comments.length, 1);
});

test("informational reviews do not revoke approval, but dismissal does", () => {
  const approval = {
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "APPROVED",
  };
  assert.equal(
    approved([approval, { ...approval, state: "COMMENTED" }], sha),
    true,
  );
  assert.equal(
    approved([approval, { ...approval, state: "DISMISSED" }], sha),
    false,
  );
});
