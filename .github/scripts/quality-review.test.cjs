const { test } = require("node:test");
const assert = require("node:assert/strict");
const {
  approved,
  readiness,
  mergeChecks,
  run,
} = require("./quality-review.cjs");
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
      reviewClient: github,
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
    reviewClient: github,
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
      if (tick === 3)
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

function fixture() {
  const pull = {
    number: 9,
    state: "open",
    draft: false,
    head: { sha },
    merge_commit_sha: "b".repeat(40),
    base: { ref: "main", repo: { full_name: "owner/repo" } },
  };
  const data = {
    pulls: [pull],
    current: pull,
    checks: [
      {
        id: 1,
        name: "Validate ci",
        app: { slug: "github-actions" },
        status: "completed",
        conclusion: "success",
      },
    ],
    reviews: [],
    comments: [],
    states: [],
    requests: 0,
  };
  const routes = Object.fromEntries(
    ["pulls", "checks", "statuses", "reviews", "comments"].map((name) => [
      name,
      () => {},
    ]),
  );
  const github = {
    paginate: async (method) => {
      const name = Object.keys(routes).find((key) => routes[key] === method);
      if (name === "statuses") return [];
      if (name) return data[name];
      throw new Error("Unexpected API call");
    },
    rest: {
      repos: {
        listPullRequestsAssociatedWithCommit: routes.pulls,
        listCommitStatusesForRef: routes.statuses,
        createCommitStatus: async (value) => data.states.push(value.state),
      },
      checks: { listForRef: routes.checks },
      pulls: {
        get: async () => ({ data: data.current }),
        listReviews: routes.reviews,
      },
      issues: {
        listComments: routes.comments,
        createComment: async (value) => {
          data.requests++;
          data.comments.push({
            user: { login: "github-actions[bot]" },
            body: value.body,
          });
        },
      },
    },
  };
  const options = {
    github,
    reviewClient: github,
    context: {
      repo: { owner: "owner", repo: "repo" },
      payload: { workflow_run: { event: "pull_request", head_sha: sha } },
      serverUrl: "https://github.com",
      runId: 42,
    },
    core: { info() {} },
    attempts: 1,
    sleep: async () => {},
  };
  process.env.REQUIRED_CHECKS = '["Validate ci"]';
  return { data, options };
}
test("non-PR events and stale, draft or foreign PRs cannot publish success", async () => {
  const { data, options } = fixture();
  options.context.payload.workflow_run.event = "workflow_dispatch";
  await run(options);
  options.context.payload.workflow_run.event = "pull_request";
  const original = data.pulls[0];
  for (const pull of [
    { ...original, state: "closed" },
    { ...original, draft: true },
    {
      ...original,
      head: { sha: "c".repeat(40) },
      merge_commit_sha: "d".repeat(40),
    },
    { ...original, base: { ref: "main", repo: { full_name: "other/repo" } } },
  ]) {
    data.pulls = [pull];
    await run(options);
  }
  assert.deepEqual(data.states, []);
});
test("ambiguous revisions and an empty policy fail before requesting reviews", async () => {
  const { data, options } = fixture();
  data.pulls.push(data.pulls[0]);
  await assert.rejects(run(options), /unique current PR/);
  data.pulls.pop();
  process.env.REQUIRED_CHECKS = "[]";
  await assert.rejects(run(options), /policy is empty/);
  assert.equal(data.requests, 0);
});
test("manual recovery requires a full SHA and honors an existing approval", async () => {
  const { data, options } = fixture();
  options.context.payload = {};
  process.env.REVISION = "main";
  await assert.rejects(run(options), /full triggering revision/);
  process.env.REVISION = sha;
  data.reviews.push({
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "APPROVED",
  });
  await run(options);
  assert.deepEqual(data.states, ["pending", "success"]);
  assert.equal(data.requests, 0);
  delete process.env.REVISION;
});
test("failed validation times out without requesting a review", async () => {
  const { data, options } = fixture();
  data.checks[0].conclusion = "failure";
  await assert.rejects(run(options), /Validation or review incomplete/);
  assert.equal(data.requests, 0);
  assert.deepEqual(data.states, ["pending", "failure"]);
});
test("review retries are deduplicated and bounded across workflow runs", async () => {
  const { data, options } = fixture();
  options.attempts = 2;
  await assert.rejects(run(options), /Validation or review incomplete/);
  assert.equal(data.requests, 1);
  data.comments.push(
    ...[1, 2].map((id) => ({
      user: { login: "github-actions[bot]" },
      body: `<!-- quality-review:${sha}:${id}:1 -->`,
    })),
  );
  options.context.runId = 43;
  await assert.rejects(run(options), /Three review requests/);
  assert.equal(data.requests, 1);
});

test("dedicated requester posts as the maintainer and ignores earlier bot requests", async () => {
  const { data, options } = fixture();
  data.comments.push(
    ...[1, 2, 3].map((id) => ({
      user: { login: "github-actions[bot]" },
      body: `<!-- quality-review:${sha}:${id}:1 -->`,
    })),
  );
  let lookups = 0,
    requests = 0,
    ticks = 0;
  options.reviewClient = {
    rest: {
      users: {
        getAuthenticated: async () => {
          lookups++;
          return { data: { login: "maintainer" } };
        },
      },
      issues: {
        createComment: async (value) => {
          requests++;
          data.comments.push({
            user: { login: "maintainer" },
            body: value.body,
          });
        },
      },
    },
  };
  options.attempts = 3;
  options.sleep = async () => {
    ticks++;
    if (ticks === 2)
      data.reviews.push({
        user: { login: "coderabbitai[bot]" },
        commit_id: sha,
        state: "APPROVED",
      });
  };
  await run(options);
  assert.equal(lookups, 1);
  assert.equal(requests, 1);
  assert.equal(data.requests, 0);
  assert.deepEqual(data.states, ["pending", "success"]);
});
test("without a requester, manual approval can pass but no bot request is posted", async () => {
  const { data, options } = fixture();
  options.reviewClient = null;
  options.attempts = 2;
  options.sleep = async () =>
    data.reviews.push({
      user: { login: "coderabbitai[bot]" },
      commit_id: sha,
      state: "APPROVED",
    });
  await run(options);
  assert.equal(data.requests, 0);
  assert.deepEqual(data.states, ["pending", "success"]);
});
test("an invalid request token cannot publish a successful review gate", async () => {
  const { data, options } = fixture();
  options.reviewClient = {
    rest: {
      users: {
        getAuthenticated: async () => {
          throw new Error("Requester authentication failed");
        },
      },
    },
  };
  await assert.rejects(run(options), /Requester authentication failed/);
  assert.deepEqual(data.states, ["pending", "failure"]);
  assert.equal(data.requests, 0);
});

test("optional checks also block review until successful", () => {
  const required = {
    id: 1,
    name: "Validate ci",
    app: { slug: "github-actions" },
    status: "completed",
    conclusion: "success",
  };
  const extra = {
    ...required,
    id: 2,
    name: "Security gate",
    conclusion: "failure",
  };
  assert.deepEqual(readiness([required.name], [required, extra], []), [
    extra.name,
  ]);
  assert.deepEqual(
    readiness(
      [required.name],
      [required, { ...extra, status: "in_progress", conclusion: null }],
      [],
    ),
    [extra.name],
  );
  assert.deepEqual(
    readiness(
      [required.name],
      [required, { ...extra, conclusion: "success" }],
      [],
    ),
    [],
  );
  assert.deepEqual(
    readiness(
      [required.name],
      [required],
      [{ id: 1, context: "External analysis", state: "failure" }],
    ),
    ["External analysis"],
  );
  assert.deepEqual(
    readiness(
      [required.name],
      [
        required,
        { ...extra, name: "CodeRabbit after checks", status: "in_progress" },
      ],
      [{ id: 1, context: "Review passed", state: "pending" }],
    ),
    [],
  );
});

test("merge checks take precedence over later head-only reruns", () => {
  const failed = {
    id: 100,
    name: "Validate ci",
    app: { slug: "github-actions" },
    status: "completed",
    conclusion: "failure",
  };
  const passed = { ...failed, id: 101, conclusion: "success" };
  assert.deepEqual(
    readiness([failed.name], mergeChecks([failed], [passed]), []),
    [failed.name],
  );
  assert.deepEqual(readiness([failed.name], mergeChecks([], [passed]), []), []);
});

test("review-event notifications invalidate withdrawn approval and restore a valid gate", async () => {
  const { data, options } = fixture();
  options.context.payload.workflow_run.event = "pull_request_review";
  data.reviews.push({
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "APPROVED",
  });
  await run(options);
  data.reviews.push({
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "DISMISSED",
  });
  await assert.rejects(run(options), /Validation or review incomplete/);
  assert.deepEqual(data.states, ["pending", "success", "pending", "failure"]);
  data.reviews.push({
    user: { login: "coderabbitai[bot]" },
    commit_id: sha,
    state: "APPROVED",
  });
  await run(options);
  assert.equal(data.states.at(-1), "success");
});
