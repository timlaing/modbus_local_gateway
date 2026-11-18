const { test, before } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const workflow = fs.readFileSync(
  path.join(__dirname, "../workflows/dependabot-auto-merge.yml"),
  "utf8",
);
const block = workflow.split("          script: |\n")[1];
before(() => assert.ok(block, "The trusted merge script must be present"));
const script = block
  .split("\n")
  .map((line) => (line.startsWith("            ") ? line.slice(12) : line))
  .join("\n");
const execute = new (Object.getPrototypeOf(async function () {}).constructor)(
  "github",
  "context",
  "core",
  "process",
  script,
);
const required = JSON.parse(
  fs.readFileSync(path.join(__dirname, "../workflow-policy.json"), "utf8"),
).required_checks;
function fixture(status, enforced = true) {
  const calls = [];
  const sha = "a".repeat(40);
  const pr = {
    number: 1,
    state: "open",
    head: { sha },
    base: { ref: "main" },
    user: { login: "dependabot[bot]" },
    node_id: "PR_id",
    mergeable_state: "clean",
  };
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: pr }),
        merge: async (args) => {
          calls.push(["merge", args]);
          if (status) throw Object.assign(new Error("Rejected"), { status });
          return { data: { merged: true } };
        },
      },
    },
    request: async () => ({
      data: [
        {
          type: "required_status_checks",
          parameters: {
            required_status_checks: enforced
              ? required
                  .filter(
                    (name) =>
                      enforced !== "missing-notifier" ||
                      name !== "Review notifier policy",
                  )
                  .map((context) => ({ context, integration_id: 15368 }))
              : [],
          },
        },
      ],
    }),
    graphql: async (query, args) => calls.push(["auto", args]),
  };
  const run = () =>
    execute(
      github,
      { repo: { owner: "owner", repo: "repo" }, payload: { pull_request: pr } },
      { notice() {} },
      {
        env: {
          UPDATE_TYPE: "version-update:semver-patch",
          REQUIRED_CHECKS: JSON.stringify(required),
        },
      },
    );
  return { run, calls, sha, pr, github };
}
test("an already-clean PR merges natively with the checked head", async () => {
  const f = fixture();
  await f.run();
  assert.deepEqual(
    f.calls.map((call) => call[0]),
    ["merge"],
  );
  assert.equal(f.calls[0][1].sha, f.sha);
});
test("a protection race falls back to native auto-merge for the same head", async () => {
  const f = fixture(405);
  await f.run();
  assert.deepEqual(
    f.calls.map((call) => call[0]),
    ["merge", "auto"],
  );
  assert.equal(f.calls[1][1].oid, f.sha);
});
test("a changed head is never queued after a failed direct merge", async () => {
  const f = fixture(409);
  await assert.rejects(f.run(), /Rejected/);
  assert.deepEqual(
    f.calls.map((call) => call[0]),
    ["merge"],
  );
});
test("no merge path activates before the intended gates are enforced", async () => {
  const f = fixture(undefined, false);
  await f.run();
  assert.deepEqual(f.calls, []);
});

test("partial enforcement without notifier policy cannot activate merging", async () => {
  const f = fixture(undefined, "missing-notifier");
  await f.run();
  assert.deepEqual(f.calls, []);
});
test("a PR becoming clean during auto-merge activation is re-read and merged at the same SHA", async () => {
  const f = fixture();
  f.pr.mergeable_state = "blocked";
  f.github.graphql = async () => {
    f.pr.mergeable_state = "clean";
    throw new Error("Pull request is in clean status");
  };
  await f.run();
  assert.deepEqual(
    f.calls.map((call) => call[0]),
    ["merge"],
  );
  assert.equal(f.calls[0][1].sha, f.sha);
});
test("an unrelated auto-merge error is never converted into a direct merge", async () => {
  const f = fixture();
  f.pr.mergeable_state = "blocked";
  f.github.graphql = async () => {
    throw new Error("Permission denied");
  };
  await assert.rejects(f.run(), /Permission denied/);
  assert.deepEqual(f.calls, []);
});
