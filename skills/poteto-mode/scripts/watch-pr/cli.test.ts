import { describe, expect, it } from "bun:test";
import { type CliRuntime, main, parseArgs } from "./cli.ts";
import { fakeReader, passingCheck, pendingCheck } from "./fakes.test-helper.ts";
import { renderJson, renderPretty } from "./render.ts";
import type { GitHubReader, WatcherVerdict } from "./types.ts";
import { parsePrNumber } from "./types.ts";

const silentIo = { stdout: () => {}, stderr: () => {} };

describe("GitHub readiness after a push", () => {
  for (const firstCheck of [
    passingCheck("DCO"),
    { ...passingCheck("invalidate"), kind: "skipped", reportedState: "SKIPPED" },
  ] as const) {
    for (const mode of ["single", "stack"] as const) {
      it(`waits for build checks after only ${firstCheck.name} in ${mode} mode`, async () => {
        let phase = 0;
        const initializing = fakeReader({
          facts: { mergeStateStatus: "UNKNOWN", isDraft: true },
          fastPath: { kind: "checks", checks: [firstCheck] },
        });
        const building = fakeReader({
          facts: { mergeStateStatus: "BLOCKED", isDraft: true },
          fastPath: { kind: "checks", checks: [firstCheck, pendingCheck("build")] },
          commitRollups: [{ oid: "head", state: "PENDING" }],
        });
        const complete = fakeReader({
          facts: { isDraft: true },
          fastPath: { kind: "checks", checks: [firstCheck, passingCheck("build")] },
        });
        const current = () => phase === 0 ? initializing : phase === 1 ? building : complete;
        const reader: GitHubReader = {
          ...initializing,
          pullRequest: (context) => current().pullRequest(context),
          checksFastPath: (context) => current().checksFastPath(context),
          commitRollups: (context) => current().commitRollups(context),
        };
        const harness = testRuntime(reader);
        const code = await main([
          "--owner", "owner", "--repo", "repo", "--pr", "1", "--allow-draft",
          ...(mode === "stack" ? ["--stack"] : []),
        ], {
          ...harness.runtime,
          clock: {
            now: () => phase * 60,
            observedAt: () => "2026-11-11T06:13:24.775Z",
            async sleep() { phase += 1; },
          },
        });
        expect(code).toBe(0);
        expect(phase).toBe(2);
        const events: unknown[] = harness.stdout.map((line) => JSON.parse(line));
        expect(events).toContainEqual(expect.objectContaining({ kind: "WAITING" }));
        expect(events.at(-1)).toMatchObject({ kind: "READY" });
        expect(harness.stdout.at(-1)).toContain('"name":"build"');
      });
    }
  }

  it("times out instead of reporting READY when GitHub stays unknown", async () => {
    const harness = testRuntime(fakeReader({ facts: { mergeStateStatus: "UNKNOWN" } }));
    let now = 0;
    const code = await main([
      "--owner", "owner", "--repo", "repo", "--pr", "1", "--timeout", "5",
    ], {
      ...harness.runtime,
      clock: {
        now: () => now,
        observedAt: () => "2026-11-11T06:13:24.775Z",
        async sleep(seconds) { now += seconds; },
      },
    });
    expect(code).toBe(5);
    expect(now).toBe(5);
    expect(JSON.parse(harness.stdout.at(-1) ?? "null")).toMatchObject({ kind: "TIMEOUT" });
    expect(harness.stdout.join("")).not.toContain('"kind":"READY"');
  });

  it("shows unknown readiness in a status-only table", async () => {
    const harness = testRuntime(fakeReader({ facts: { mergeStateStatus: "UNKNOWN" } }));
    const code = await main([
      "--owner", "owner", "--repo", "repo", "--pr", "1", "--status-only", "--pretty",
    ], harness.runtime);
    expect(code).toBe(0);
    expect(harness.stdout.join("")).toContain("GitHub is still computing mergeability");
    expect(harness.stdout.join("")).toContain("computing |");
  });
});

function testRuntime(reader: GitHubReader): {
  readonly runtime: CliRuntime;
  readonly stdout: string[];
  readonly stderr: string[];
} {
  const stdout: string[] = [];
  const stderr: string[] = [];
  return {
    stdout,
    stderr,
    runtime: {
      reader,
      clock: {
        now: () => 0,
        observedAt: () => "2026-07-26T00:00:00.000Z",
        async sleep() {
          throw new Error("test unexpectedly slept");
        },
      },
      stdout: (value) => stdout.push(value),
      stderr: (value) => stderr.push(value),
    },
  };
}

describe("parseArgs", () => {
  it("uses the specified defaults", () => {
    expect(parseArgs([], silentIo)).toMatchObject({
      owner: null,
      repo: null,
      pr: null,
      mode: "single",
      stackPrs: [],
      statusOnly: false,
      pretty: false,
      polling: {
        interval: 60,
        sweepInterval: 300,
        timeout: 0,
        maxQueryErrors: 5,
        allowDraft: false,
      },
    });
  });

  it("parses a frozen queued stack bottom-to-top", () => {
    const parsed = parseArgs(
      [
        "--queued-stack",
        "--stack-prs",
        "#10, 11,#12",
        "--interval",
        "2.5",
        "--sweep-interval",
        "30",
        "--timeout",
        "0",
        "--max-query-errors",
        "3",
        "--allow-draft",
        "--pretty",
      ],
      silentIo
    );
    expect(parsed.mode).toBe("queued-stack");
    expect(parsed.stackPrs.map(Number)).toEqual([10, 11, 12]);
    expect(parsed.polling).toEqual({
      interval: 2.5,
      sweepInterval: 30,
      timeout: 0,
      maxQueryErrors: 3,
      allowDraft: true,
    });
    expect(parsed.pretty).toBe(true);
  });

  it("rejects every invalid mode and numeric shape as usage", async () => {
    const invalid = [
      ["--unknown"],
      ["--interval", "0"],
      ["--sweep-interval", "-1"],
      ["--timeout", "-1"],
      ["--max-query-errors", "1.5"],
      ["--stack", "--queued-stack"],
      ["--stack-prs", "1,2"],
      ["--queued-stack", "--stack-prs", "1,1"],
    ];
    for (const argv of invalid) {
      const harness = testRuntime(fakeReader());
      expect(await main(argv, harness.runtime)).toBe(64);
      expect(harness.stdout).toEqual([]);
      expect(harness.stderr.join("")).toContain("error:");
    }
  });
});

describe("rendering", () => {
  const context = {
    owner: "owner",
    repo: "repo",
    number: parsePrNumber(1),
  };
  const status = {
    schemaVersion: 1,
    sequence: 1,
    observedAt: "2026-07-26T00:00:00.000Z",
    mode: "single",
    kind: "STATUS",
    terminal: true,
    exitCode: 0,
    reason: "status-only",
    rows: [
      {
        kind: "merged",
        context,
        facts: {
          context,
          mergeable: "MERGEABLE",
          mergeStateStatus: "CLEAN",
          reviewDecision: "APPROVED",
          headRefOid: "head",
          headRefName: "feature",
          baseRefName: "main",
          state: "MERGED",
          mergedAt: "now",
          isDraft: false,
        },
      },
    ],
  } satisfies WatcherVerdict;

  it("emits compact valid JSON by default", () => {
    const rendered = renderJson(status);
    expect(rendered.endsWith("\n")).toBe(true);
    expect(JSON.parse(rendered)).toEqual(status);
  });

  it("renders the Markdown table from the same verdict only", () => {
    const rendered = renderPretty(status);
    expect(rendered).toContain("| PR | CI | Review | Merge |");
    expect(rendered).toContain(
      "| [#1](https://github.com/owner/repo/pull/1) | \u2014 | \u2014 | ✅ merged |"
    );
  });
});

describe("main", () => {
  it("returns EX_USAGE 64 and writes usage errors only to stderr", async () => {
    const harness = testRuntime(fakeReader());
    expect(await main(["--interval", "0"], harness.runtime)).toBe(64);
    expect(harness.stdout).toEqual([]);
    expect(harness.stderr.join("")).toContain(
      "option '--interval <seconds>' argument '0' is invalid"
    );
  });

  it("bypasses the queue machine for queued-stack status-only", async () => {
    const reader = fakeReader();
    const harness = testRuntime(reader);
    const code = await main(
      [
        "--owner",
        "owner",
        "--repo",
        "repo",
        "--queued-stack",
        "--stack-prs",
        "1",
        "--status-only",
      ],
      harness.runtime
    );
    expect(code).toBe(0);
    expect(harness.stdout).toHaveLength(1);
    const verdict: unknown = JSON.parse(harness.stdout[0]);
    expect(verdict).toMatchObject({
      kind: "STATUS",
      terminal: true,
      exitCode: 0,
      mode: "queued-stack",
    });
    expect(harness.stdout[0]).not.toContain('"kind":"QUEUE"');
  });

  it("returns exit 4 for a hidden GitHub-side CI refusal", async () => {
    const reader = fakeReader({
      facts: { mergeStateStatus: "BLOCKED" },
      fastPath: { kind: "checks", checks: [passingCheck()] },
      commitRollups: [{ oid: "head", state: "FAILURE" }],
    });
    const harness = testRuntime(reader);
    const code = await main(
      ["--owner", "owner", "--repo", "repo", "--pr", "1"],
      harness.runtime
    );
    expect(code).toBe(4);
    expect(harness.stdout).toHaveLength(1);
    expect(JSON.parse(harness.stdout[0])).toMatchObject({
      kind: "BLOCKER",
      exitCode: 4,
      blocker: {
        kind: "failing-checks",
        ci: { kind: "ci-github-rejected" },
      },
    });
  });

  it("shows help without touching the reader", async () => {
    const reader = fakeReader();
    const harness = testRuntime(reader);
    expect(await main(["--help"], harness.runtime)).toBe(0);
    expect(harness.stdout.join("")).toContain("JSON (NDJSON while polling)");
    expect(reader.calls).toEqual([]);
  });
});
