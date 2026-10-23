import { afterEach, describe, expect, it } from "bun:test";
import {
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  writeFile,
} from "node:fs/promises";
import { realpathSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  NotFoundError,
  UserError,
  openStore,
  parseVerdict,
  type Forge,
  type OpenStoreOptions,
  type Store,
} from "./store.ts";

const SCRIPT = join(import.meta.dir, "orch.ts");
const directories: string[] = [];
const handles: Store[] = [];

interface RunResult {
  readonly code: number;
  readonly stdout: string;
  readonly stderr: string;
}

async function makeDirectory(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "orch-test-"));
  directories.push(directory);
  return directory;
}

function useStore(
  directory: string,
  options?: OpenStoreOptions
): Store {
  const store = openStore(directory, options);
  handles.push(store);
  return store;
}

async function initializedStore(): Promise<{
  readonly directory: string;
  readonly store: Store;
}> {
  const directory = await makeDirectory();
  const store = useStore(directory);
  await store.init();
  return { directory, store };
}

function git({
  args,
  repo,
}: {
  args: readonly string[];
  repo: string;
}): string {
  const result = Bun.spawnSync(["git", "-C", repo, ...args]);
  if (result.exitCode !== 0) {
    throw new Error(
      `git ${args.join(" ")} failed: ${result.stderr.toString()}`
    );
  }
  return result.stdout.toString().trim();
}

async function makeGitStack(directory: string, rootBranch = "main"): Promise<{
  readonly repo: string;
  readonly mergedSha: string;
  readonly closedSha: string;
  readonly openSha: string;
  readonly draftSha: string;
}> {
  const repo = join(directory, "repo");
  await mkdir(repo);
  git({ repo, args: ["init", "--initial-branch=main"] });
  git({ repo, args: ["config", "user.name", "Orch Test"] });
  git({ repo, args: ["config", "user.email", "orch@example.com"] });
  await writeFile(join(repo, "main.txt"), "main\n");
  git({ repo, args: ["add", "."] });
  git({ repo, args: ["commit", "-m", "main"] });
  git({ repo, args: ["update-ref", "refs/remotes/origin/main", "HEAD"] });
  git({
    repo,
    args: ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main"],
  });
  if (rootBranch !== "main") {
    git({ repo, args: ["checkout", "-b", rootBranch] });
  }

  const branches = [
    "stack/merged",
    "stack/closed",
    "stack/open",
    "stack/draft",
  ];
  for (const [index, branch] of branches.entries()) {
    git({ repo, args: ["checkout", "-b", branch] });
    await writeFile(join(repo, `stack-${index}.txt`), `${branch}\n`);
    git({ repo, args: ["add", "."] });
    git({ repo, args: ["commit", "-m", branch] });
  }
  git({ repo, args: ["checkout", "stack/open"] });

  return {
    repo,
    mergedSha: git({ repo, args: ["rev-parse", "stack/merged"] }),
    closedSha: git({ repo, args: ["rev-parse", "stack/closed"] }),
    openSha: git({ repo, args: ["rev-parse", "stack/open"] }),
    draftSha: git({ repo, args: ["rev-parse", "stack/draft"] }),
  };
}

type FixtureState = "open" | "draft" | "merged" | "closed";

interface FixturePr {
  readonly number: number;
  readonly state: FixtureState;
  readonly head: string;
  readonly base: string;
}

const FORGE_FIXTURES: Readonly<
  Record<
    Forge,
    {
      readonly fields: string;
      readonly row: (pr: FixturePr) => Record<string, unknown>;
    }
  >
> = {
  gh: {
    fields: "number,state,headRefName,baseRefName",
    row: ({ number, state, head, base }) => ({
      number,
      state: state === "draft" ? "OPEN" : state.toUpperCase(),
      headRefName: head,
      baseRefName: base,
    }),
  },
  origin: {
    fields: "number,status,headRef,baseRef",
    row: ({ number, state, head, base }) => ({
      number,
      status: state,
      headRef: head,
      baseRef: base,
    }),
  },
};

function forgeRows(
  forge: Forge,
  prs: readonly FixturePr[]
): string {
  return JSON.stringify(prs.map((pr) => FORGE_FIXTURES[forge].row(pr)));
}

async function withFakeForge<T>({
  directory,
  forge,
  operation,
  currentRows,
  rootBranch = "main",
  rows = {},
}: {
  directory: string;
  forge: Forge;
  operation: () => Promise<T>;
  currentRows?: string;
  rootBranch?: string;
  rows?: Readonly<Record<string, readonly FixturePr[]>>;
}): Promise<T> {
  const bin = join(directory, "bin");
  const outputPath = join(directory, "forge-output.txt");
  await mkdir(bin, { recursive: true });
  await writeFile(
    outputPath,
    `${
      currentRows ??
      forgeRows(forge, [
        {
          number: 11,
          state: "open",
          head: "stack/open",
          base: "stack/closed",
        },
      ])
    }\n`
  );
  const { fields } = FORGE_FIXTURES[forge];
  const list = (filter: string, branch: string): string =>
    `pr list ${filter} ${branch} --state all --json ${fields}`;
  const queries: Readonly<Record<string, readonly FixturePr[]>> = {
    "--head stack/closed": [
      { number: 13, state: "closed", head: "stack/closed", base: "stack/merged" },
    ],
    "--head stack/merged": [
      { number: 10, state: "merged", head: "stack/merged", base: rootBranch },
    ],
    [`--head ${rootBranch}`]: [],
    "--base stack/open": [
      { number: 14, state: "draft", head: "stack/draft", base: "stack/open" },
      { number: 15, state: "closed", head: "stack/abandoned", base: "stack/open" },
    ],
    "--base stack/draft": [],
    ...rows,
  };
  await writeFile(join(directory, "forge-queries.txt"), "");
  const fake = join(bin, forge);
  await writeFile(
    fake,
    `#!/usr/bin/env bash
set -euo pipefail
if [ "$(pwd -P)" != "${realpathSync(join(directory, "repo"))}" ]; then
  printf '${forge} ran outside the fixture repo: %s\\n' "$(pwd -P)" >&2
  exit 2
fi
printf '%s\\n' "$*" >> "${join(directory, "forge-queries.txt")}"
case "$*" in
  "${list("--head", "stack/open")}")
    cat "${outputPath}"
    ;;
${Object.entries(queries).map(([query, prs]) => {
  const [filter, branch] = query.split(" ");
  return `  "${list(filter!, branch!)}")
    printf '%s\\n' '${forgeRows(forge, prs)}'
    ;;`;
}).join("\n")}
  *)
    printf 'unexpected ${forge} arguments: %s\\n' "$*" >&2
    exit 2
    ;;
esac
`
  );
  await chmod(fake, 0o755);

  const originalPath = process.env.PATH;
  process.env.PATH = `${bin}:${originalPath ?? ""}`;
  try {
    return await operation();
  } finally {
    if (originalPath === undefined) {
      delete process.env.PATH;
    } else {
      process.env.PATH = originalPath;
    }
  }
}

function runCli(
  args: readonly string[],
  env: Readonly<Record<string, string | undefined>> = process.env
): RunResult {
  const result = Bun.spawnSync([process.execPath, SCRIPT, ...args], { env });
  return {
    code: result.exitCode,
    stdout: result.stdout.toString(),
    stderr: result.stderr.toString(),
  };
}

afterEach(async () => {
  for (const store of handles.splice(0).reverse()) {
    await store.close();
  }
  for (const directory of directories.splice(0)) {
    await rm(directory, { recursive: true, force: true });
  }
});

describe("Store", () => {
  it("initializes an idempotent plain-file store and releases its lock", async () => {
    const directory = await makeDirectory();
    const store = useStore(directory);

    expect(await store.init()).toEqual({ store: directory });
    const firstUnits = await readFile(join(directory, "units.tsv"), "utf8");
    const firstLedger = await readFile(
      join(directory, "ledger.tsv"),
      "utf8"
    );

    expect(await store.init()).toEqual({ store: directory });
    expect(await readFile(join(directory, "units.tsv"), "utf8")).toBe(
      firstUnits
    );
    expect(await readFile(join(directory, "ledger.tsv"), "utf8")).toBe(
      firstLedger
    );
    expect((await readdir(directory)).sort()).toEqual([
      ".orch.lock",
      "frontier.json",
      "gates.md",
      "inbox",
      "ledger.tsv",
      "preferences.md",
      "units.tsv",
    ]);

    await store.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("composes unit add, set, get, list, and counts", async () => {
    const { store } = await initializedStore();

    expect(
      await store.units.add({
        id: "u1",
        track: "build",
        brief: "briefs/u1.md",
      })
    ).toMatchObject({ id: "u1", state: "pending" });
    expect(
      await store.units.add({ id: "=SUM(A1)", track: "+build" })
    ).toMatchObject({ id: "'=SUM(A1)", track: "'+build" });

    const updated = await store.units.set({
      id: "u1",
      state: "done",
      branch: "poteto/u1",
      pr: 184530,
      sha: "abc123",
    });
    expect(updated).toEqual({
      id: "u1",
      track: "build",
      state: "done",
      branch: "poteto/u1",
      pr: "184530",
      sha: "abc123",
      brief: "briefs/u1.md",
    });
    expect(await store.units.get("u1")).toEqual(updated);
    expect(
      await store.units.list({ state: "done", track: "build" })
    ).toEqual([updated]);
    expect(await store.units.counts()).toEqual({ done: 1, pending: 1 });
    await expect(
      store.units.add({ id: "u1", track: "build" })
    ).rejects.toThrow("unit u1 already exists");
    await expect(
      store.units.set({ id: "missing", state: "done" })
    ).rejects.toBeInstanceOf(NotFoundError);
  });

  it("records, replaces, checks, and summarizes typed ledger verdicts", async () => {
    const { store } = await initializedStore();

    try {
      await store.ledger.check({ pr: 184530, sha: "abc123" });
      throw new Error("expected ledger check to fail");
    } catch (error) {
      expect(error).toBeInstanceOf(NotFoundError);
      if (error instanceof NotFoundError) {
        expect(error.output).toEqual({
          compact: "NOT-VERIFIED",
          json: {
            pr: "184530",
            sha: "abc123",
            verdict: "NOT-VERIFIED",
          },
        });
      }
    }
    expect(() => parseVerdict("looks-good")).toThrow("verdict must be");

    const recorded = await store.ledger.record({
      pr: 184530,
      sha: "abc123",
      verdict: "unit-test-verified",
      evidence: "reports/verify.md",
      verifier: "opus",
    });
    expect(await store.ledger.check({ pr: 184530, sha: "abc123" })).toEqual(
      recorded
    );
    expect(await store.ledger.summary()).toEqual({
      "unit-test-verified": 1,
    });

    await store.ledger.record({
      pr: 184530,
      sha: "abc123",
      verdict: "live-ui-verified",
      evidence: "reports/live.md",
    });
    expect(await store.ledger.summary()).toEqual({
      "live-ui-verified": 1,
    });
  });

  it("pushes, peeks, and atomically drains inbox pointers", async () => {
    const { directory, store } = await initializedStore();

    const first = await store.inbox.push({
      agent: "worker-1",
      unit: "u1",
      status: "done",
      report: "reports/u1.md",
    });
    expect(first.pointer).toMatchObject({ unit: "u1", status: "done" });
    expect(first.filename).toEndWith(".tsv");
    await store.inbox.push({
      agent: "worker-2",
      unit: "u2",
      status: "failed",
    });

    expect(await store.inbox.count()).toBe(2);
    expect(await store.inbox.peek()).toHaveLength(2);
    expect(await store.inbox.count()).toBe(2);
    expect(await store.inbox.drain()).toHaveLength(2);
    expect(await store.inbox.count()).toBe(0);
    expect(await readdir(join(directory, "inbox"))).toEqual([]);
    expect(
      (await readdir(directory)).filter((name) =>
        name.startsWith(".inbox-drain-")
      )
    ).toEqual([]);
  });

  it("replaces a stale lock whose holder pid is dead", async () => {
    const { directory } = await initializedStore();
    const exited = Bun.spawn(["true"]);
    await exited.exited;
    await writeFile(join(directory, ".orch.lock"), `${exited.pid}\n`);

    const stale: string[] = [];
    const recovered = useStore(directory, {
      onStaleLock: (holder) => stale.push(holder),
    });
    expect(
      await recovered.units.add({ id: "u1", track: "build" })
    ).toMatchObject({ id: "u1" });
    expect(stale).toEqual([String(exited.pid)]);
    await recovered.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("blocks a writer and steals the pid lock only with force", async () => {
    const { directory, store } = await initializedStore();
    await store.close();
    await writeFile(join(directory, ".orch.lock"), `${process.pid}\n`);

    const blocked = useStore(directory);
    await expect(
      blocked.units.add({ id: "u1", track: "build" })
    ).rejects.toThrow(`store lock held by pid ${process.pid}`);

    const stolen: string[] = [];
    const forced = useStore(directory, {
      force: true,
      onLockStolen: (holder) => stolen.push(holder),
    });
    expect(
      await forced.units.add({ id: "u1", track: "build" })
    ).toMatchObject({ id: "u1" });
    expect(stolen).toEqual([String(process.pid)]);
    await forced.close();
    expect(await readdir(directory)).not.toContain(".orch.lock");
  });

  it("parks gates, stores standing orders, and renders status", async () => {
    const { directory, store } = await initializedStore();
    await store.units.add({ id: "u1", track: "build" });
    expect(
      await store.gates.park({
        id: "release",
        question: "Ship now?",
        options: "ship,wait",
        defaultAnswer: "wait",
      })
    ).toMatchObject({ kind: "open", id: "release" });
    expect(
      await store.standing.add({ line: "Never force push." })
    ).toEqual({ number: 1, line: "Never force push." });

    const first = await store.status.render();
    expect(first.changed).toBe("first render");
    expect(first.summary.openGateIds).toEqual(["release"]);
    expect(await readFile(join(directory, "status.md"), "utf8")).toContain(
      "| release | open | Ship now? |"
    );
    expect((await store.status.render()).changed).toBe("no derived changes");

    expect(
      await store.gates.resolve({ id: "release", answer: "ship" })
    ).toMatchObject({ kind: "resolved", answer: "ship" });
    expect((await store.status.render()).changed).toBe("open gates 1->0");
    expect(await store.gates.list()).toEqual([]);
    expect(await store.standing.show()).toEqual([
      { number: 1, line: "Never force push." },
    ]);
  });

  for (const forge of ["gh", "origin"] as const) {
    it(`resolves the ordered frontier from the ${forge} base chain and validates an optional pin`, async () => {
      const { directory, store } = await initializedStore();
      const stack = await makeGitStack(directory);
      const forgeParams = forge === "gh" ? {} : { forge };

      await withFakeForge({
        directory,
        forge,
        operation: async () => {
          expect(
            await store.frontier.set({ repo: stack.repo, ...forgeParams })
          ).toEqual({
            generation: 1,
            prs: [
              {
                pr: 10,
                branches: "stack/merged",
                sha: stack.mergedSha,
                state: "MERGED",
              },
              {
                pr: 13,
                branches: "stack/closed",
                sha: stack.closedSha,
                state: "CLOSED",
              },
              {
                pr: 11,
                branches: "stack/open",
                sha: stack.openSha,
                state: "OPEN",
              },
              {
                pr: 14,
                branches: "stack/draft",
                sha: stack.draftSha,
                state: "OPEN",
              },
            ],
            lowestUnmerged: 11,
          });
          expect(
            (
              await store.frontier.set({
                repo: stack.repo,
                ...forgeParams,
                prs: [10, 13, 11, 14],
              })
            ).generation
          ).toBe(2);
          expect((await store.frontier.show()).generation).toBe(2);
          await expect(
            store.frontier.set({
              repo: stack.repo,
              ...forgeParams,
              prs: [10, 11, 12],
            })
          ).rejects.toThrow(
            "frontier pin mismatch: missing from resolved chain: 12; extra in resolved chain: 13,14"
          );
          await expect(
            store.frontier.set({
              repo: stack.repo,
              ...forgeParams,
              prs: [13, 10, 11, 14],
            })
          ).rejects.toThrow(
            "frontier pin mismatch: order differs: expected 13,10,11,14; resolved 10,13,11,14"
          );
          await expect(
            store.frontier.set({
              repo: stack.repo,
              ...forgeParams,
              prs: [10, 10],
            })
          ).rejects.toThrow("--prs must not contain duplicates");
        },
      });
    });

    it(`rejects unparseable ${forge} output loudly`, async () => {
      const { directory, store } = await initializedStore();
      const stack = await makeGitStack(directory);

      await withFakeForge({
        directory,
        forge,
        currentRows: "this line is not forge output",
        operation: async () => {
          await expect(
            store.frontier.set({ repo: stack.repo, forge })
          ).rejects.toThrow(
            `${forge} pr list --head stack/open output is not valid JSON`
          );
        },
      });
    });
  }

  it("names the missing pull request when a chain branch has none", async () => {
    const { directory, store } = await initializedStore();
    const stack = await makeGitStack(directory);

    await withFakeForge({
      directory,
      forge: "gh",
      currentRows: "[]",
      operation: async () => {
        await expect(store.frontier.set({ repo: stack.repo })).rejects.toThrow(
          "branch stack/open has no pull request; open one with gh pr create"
        );
      },
    });
  });

  it("rejects malformed TSV, verdict, frontier, and inbox data", async () => {
    const { directory, store } = await initializedStore();

    await writeFile(join(directory, "units.tsv"), "wrong\n");
    await expect(store.units.list()).rejects.toThrow(
      "units.tsv has an invalid header"
    );
    await writeFile(
      join(directory, "units.tsv"),
      "id\ttrack\tstate\tbranch\tpr\tsha\tbrief\nshort\trow\n"
    );
    await expect(store.units.list()).rejects.toThrow(
      "units.tsv has a malformed row"
    );

    await writeFile(
      join(directory, "ledger.tsv"),
      "pr\tsha\tverdict\tevidence\tverifier\tts\n1\tsha\tinvalid\treport\tme\tnow\n"
    );
    await expect(store.ledger.summary()).rejects.toThrow(
      "ledger.tsv has invalid verdict invalid"
    );

    await writeFile(join(directory, "frontier.json"), '{"generation":"1"}\n');
    await expect(store.frontier.show()).rejects.toThrow(
      "frontier.json has an invalid shape"
    );

    await writeFile(join(directory, "inbox", "bad.tsv"), "too\tshort\n");
    await expect(store.inbox.peek()).rejects.toThrow(
      "inbox pointer bad.tsv is malformed"
    );
  });

  it("rejects operations after close", async () => {
    const { store } = await initializedStore();
    await store.close();
    await expect(store.units.list()).rejects.toThrow("store is closed");
    await expect(store.status.render()).rejects.toBeInstanceOf(UserError);
  });
});

describe("orch CLI", () => {
  for (const forge of ["gh", "origin"] as const) {
    for (const mode of [
      "explicit integration root",
      "remote-only integration root",
      "origin/HEAD default",
      "main fallback",
      "main origin/HEAD default",
    ] as const) {
      it(`resolves and persists the pinned ${forge} CLI frontier with ${mode}`, async () => {
        const directory = await makeDirectory();
        const integration = !mode.startsWith("main");
        const rootBranch = integration ? "integration/release" : "main";
        const stack = await makeGitStack(directory, rootBranch);
        const explicit = mode.includes("integration root");
        if (mode === "remote-only integration root") {
          git({
            repo: stack.repo,
            args: ["update-ref", "refs/remotes/origin/integration/release", rootBranch],
          });
          git({ repo: stack.repo, args: ["branch", "-D", rootBranch] });
        } else if (mode === "origin/HEAD default") {
          git({
            repo: stack.repo,
            args: ["update-ref", "refs/remotes/origin/integration/release", rootBranch],
          });
          git({
            repo: stack.repo,
            args: ["symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/integration/release"],
          });
        } else if (mode === "main fallback") {
          git({
            repo: stack.repo,
            args: ["symbolic-ref", "--delete", "refs/remotes/origin/HEAD"],
          });
        }
        expect(runCli(["--store", directory, "init"]).code).toBe(0);
        await withFakeForge({
          directory,
          forge,
          rootBranch,
          operation: async () => {
            const result = runCli([
              "--store", directory, "--json", "frontier", "set",
              "--repo", stack.repo, "--forge", forge,
              ...(explicit ? ["--base", rootBranch] : []),
              "--prs", "10,13,11,14",
            ]);
            expect(result.stderr).toBe("");
            expect(result.code).toBe(0);
            const expected = {
              generation: 1,
              prs: [
                { pr: 10, branches: "stack/merged", sha: stack.mergedSha, state: "MERGED" },
                { pr: 13, branches: "stack/closed", sha: stack.closedSha, state: "CLOSED" },
                { pr: 11, branches: "stack/open", sha: stack.openSha, state: "OPEN" },
                { pr: 14, branches: "stack/draft", sha: stack.draftSha, state: "OPEN" },
              ],
              lowestUnmerged: 11,
            };
            expect(JSON.parse(result.stdout)).toEqual(expected);
            const shown = runCli(["--store", directory, "--json", "frontier", "show"]);
            expect(shown.code).toBe(0);
            expect(JSON.parse(shown.stdout)).toEqual(expected);
            expect(JSON.parse(await readFile(join(directory, "frontier.json"), "utf8"))).toEqual(expected);
            if (explicit) {
              expect(git({
                repo: stack.repo,
                args: ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
              })).toBe("origin/main");
            }
            expect(await readFile(join(directory, "forge-queries.txt"), "utf8"))
              .not.toContain(`--head ${rootBranch} `);
          },
        });
      });
    }

    it(`reports the missing integration PR with ${forge} when --base is omitted`, async () => {
      const directory = await makeDirectory();
      const stack = await makeGitStack(directory, "integration/release");
      expect(runCli(["--store", directory, "init"]).code).toBe(0);
      const before = await readFile(join(directory, "frontier.json"), "utf8");
      await withFakeForge({
        directory,
        forge,
        rootBranch: "integration/release",
        operation: async () => {
          const result = runCli([
            "--store", directory, "frontier", "set", "--repo", stack.repo,
            "--forge", forge,
          ]);
          expect(result.code).toBe(1);
          expect(result.stderr).toContain("branch integration/release has no pull request");
          expect(result.stderr).not.toContain("unexpected");
          expect(await readFile(join(directory, "frontier.json"), "utf8")).toBe(before);
        },
      });
    });

    it(`returns an exact empty ${forge} CLI frontier at the explicit base without querying the forge`, async () => {
      const directory = await makeDirectory();
      const stack = await makeGitStack(directory, "integration/release");
      git({ repo: stack.repo, args: ["checkout", "integration/release"] });
      expect(runCli(["--store", directory, "init"]).code).toBe(0);
      await withFakeForge({
        directory,
        forge,
        rootBranch: "integration/release",
        operation: async () => {
          const result = runCli([
            "--store", directory, "--json", "frontier", "set",
            "--repo", stack.repo, "--forge", forge,
            "--base", "integration/release",
          ]);
          expect(result.code).toBe(0);
          expect(result.stderr).toBe("");
          const expected = { generation: 1, prs: [], lowestUnmerged: null };
          expect(JSON.parse(result.stdout)).toEqual(expected);
          expect(JSON.parse(await readFile(join(directory, "frontier.json"), "utf8"))).toEqual(expected);
          expect(await readFile(join(directory, "forge-queries.txt"), "utf8")).toBe("");
        },
      });
    });
  }

  it("rejects invalid and nonexistent explicit bases without changing the frontier or querying the forge", async () => {
    const directory = await makeDirectory();
    const stack = await makeGitStack(directory, "integration/release");
    expect(runCli(["--store", directory, "init"]).code).toBe(0);
    await withFakeForge({
      directory,
      forge: "gh",
      rootBranch: "integration/release",
      operation: async () => {
        const args = [
          "--store", directory, "--json", "frontier", "set", "--repo", stack.repo,
        ];
        expect(runCli([...args, "--base", "integration/release"]).code).toBe(0);
        const cliFrontier = JSON.parse(runCli([
          "--store", directory, "--json", "frontier", "show",
        ]).stdout);
        const cliBefore = await readFile(join(directory, "frontier.json"), "utf8");
        const cliQueries = await readFile(join(directory, "forge-queries.txt"), "utf8");
        const invalidBases = [
          "", "--help", "-main", "HEAD", "HEAD~1", "main^0", "main..stack/open",
          "@", "@{-1}", " integration/release ", "\tintegration/release\n",
          stack.openSha, "refs/heads/main", "bad..branch", "integration/missing",
        ];
        for (const base of invalidBases) {
          const result = runCli([...args, `--base=${base}`]);
          expect(result.code).toBe(1);
          expect(result.stderr).toMatch(
            /invalid base branch:|git check-ref-format --branch [\s\S]* failed:|base branch [\s\S]* does not exist locally or on origin/
          );
          expect(result.stderr).not.toContain("store lock held");
          expect(result.stderr).not.toContain("unknown option");
          expect(await readFile(join(directory, "frontier.json"), "utf8")).toBe(cliBefore);
          expect(await readFile(join(directory, "forge-queries.txt"), "utf8")).toBe(cliQueries);
        }
        const store = useStore(directory);
        expect(await store.frontier.set({
          repo: stack.repo,
          baseBranch: "integration/release",
        })).toEqual({ ...cliFrontier, generation: 2 });
        const before = await readFile(join(directory, "frontier.json"), "utf8");
        const queries = await readFile(join(directory, "forge-queries.txt"), "utf8");
        for (const base of invalidBases) {
          await expect(store.frontier.set({
            repo: stack.repo,
            baseBranch: base,
          })).rejects.toBeInstanceOf(UserError);
          expect(await readFile(join(directory, "frontier.json"), "utf8")).toBe(before);
          expect(await readFile(join(directory, "forge-queries.txt"), "utf8")).toBe(queries);
        }
      },
    });
  });

  const invalidFrontierScenarios: readonly {
    name: string;
    pin?: string;
    rows: Readonly<Record<string, readonly FixturePr[]>>;
    error: string;
  }[] = [
    {
      name: "pin mismatch",
      pin: "13,10,11,14",
      rows: {},
      error: "frontier pin mismatch",
    },
    {
      name: "upward cycle",
      rows: {
        "--head stack/merged": [
          { number: 10, state: "merged", head: "stack/merged", base: "stack/open" },
        ],
      },
      error: "pull request base chain loops",
    },
    {
      name: "downward cycle",
      rows: {
        "--base stack/draft": [
          { number: 11, state: "open", head: "stack/open", base: "stack/draft" },
        ],
      },
      error: "pull request base chain loops",
    },
    {
      name: "nonlinear open children",
      rows: {
        "--base stack/open": [
          { number: 14, state: "draft", head: "stack/draft", base: "stack/open" },
          { number: 16, state: "open", head: "stack/other", base: "stack/open" },
        ],
      },
      error: "stack is not linear",
    },
  ];
  for (const scenario of invalidFrontierScenarios) {
    it(`preserves the CLI frontier on an explicit-base ${scenario.name}`, async () => {
      const directory = await makeDirectory();
      const stack = await makeGitStack(directory, "integration/release");
      expect(runCli(["--store", directory, "init"]).code).toBe(0);
      const args = [
        "--store", directory, "--json", "frontier", "set",
        "--repo", stack.repo, "--base", "integration/release",
      ];
      await withFakeForge({
        directory,
        forge: "gh",
        rootBranch: "integration/release",
        operation: async () => {
          expect(runCli(args).code).toBe(0);
        },
      });
      const before = await readFile(join(directory, "frontier.json"), "utf8");
      await withFakeForge({
        directory,
        forge: "gh",
        rootBranch: "integration/release",
        rows: scenario.rows,
        operation: async () => {
          const result = runCli([
            ...args, ...(scenario.pin ? ["--prs", scenario.pin] : []),
          ]);
          expect(result.code).toBe(1);
          expect(result.stderr).toContain(scenario.error);
          expect(await readFile(join(directory, "frontier.json"), "utf8")).toBe(before);
        },
      });
    });
  }

  it("prints commander help and rejects invalid parsing with exit 1", async () => {
    const help = runCli(["--help"]);
    expect(help.code).toBe(0);
    expect(help.stdout).toContain("Commands:");
    expect(help.stdout).toContain("unit");
    expect(help.stdout).toContain("ledger");

    const frontierHelp = runCli(["frontier", "set", "--help"]);
    expect(frontierHelp.code).toBe(0);
    expect(frontierHelp.stdout).toContain("--repo <dir>");
    expect(frontierHelp.stdout).toContain("--forge <forge>");
    expect(frontierHelp.stdout).toContain("--prs <n,...>");

    const directory = await makeDirectory();
    const invalid = runCli(["--store", directory, "unit", "add", "u1"]);
    expect(invalid.code).toBe(1);
    expect(invalid.stderr).toContain("required option '--track <track>'");

    const badForge = runCli([
      "--store",
      directory,
      "frontier",
      "set",
      "--repo",
      directory,
      "--forge",
      "gt",
    ]);
    expect(badForge.code).toBe(1);
    expect(badForge.stderr).toContain("Allowed choices are gh, origin");
  });

  it("accepts ORCH_STORE and emits complete JSON", async () => {
    const directory = await makeDirectory();
    const env = { ...process.env, ORCH_STORE: directory };
    expect(runCli(["init"], env).code).toBe(0);

    const added = runCli(
      ["unit", "add", "u1", "--track", "build", "--json"],
      env
    );
    expect(added.code).toBe(0);
    expect(JSON.parse(added.stdout)).toEqual({
      id: "u1",
      track: "build",
      state: "pending",
      branch: "",
      pr: "",
      sha: "",
      brief: "",
    });
  });

  it("maps user and not-found outcomes to the preserved exit codes", async () => {
    const directory = await makeDirectory();
    expect(runCli(["--store", directory, "init"]).code).toBe(0);

    const missingRepo = runCli([
      "--store",
      directory,
      "frontier",
      "set",
    ]);
    expect(missingRepo.code).toBe(1);
    expect(missingRepo.stderr).toContain(
      "set --repo <dir> or ORCH_REPO"
    );

    const userError = runCli([
      "--store",
      directory,
      "unit",
      "add",
      "",
      "--track",
      "build",
    ]);
    expect(userError.code).toBe(1);
    expect(userError.stderr).toContain("unit id must not be empty");

    const missingUnit = runCli([
      "--store",
      directory,
      "unit",
      "get",
      "missing",
    ]);
    expect(missingUnit.code).toBe(2);
    expect(missingUnit.stderr).toContain("unit missing not found");

    const missingLedger = runCli([
      "--store",
      directory,
      "--json",
      "ledger",
      "check",
      "184530",
      "abc123",
    ]);
    expect(missingLedger.code).toBe(2);
    expect(JSON.parse(missingLedger.stdout)).toEqual({
      pr: "184530",
      sha: "abc123",
      verdict: "NOT-VERIFIED",
    });
    expect(missingLedger.stderr).toBe("");
  });
});
