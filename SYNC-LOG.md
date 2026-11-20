# Sync log

Each check against [`cursor/plugins/pstack`](https://github.com/cursor/plugins/tree/main/pstack), newest first. A check with no upstream change gets an entry too.

| Date | Upstream | Result |
|---|---|---|
| 2026-11-20 | 0.15.46 | Second check today. No change in pstack. Upstream repo head `aaeb0ea`. No new issues or PRs. #25 has no reply or new commits since we asked for a smaller version. #18 is still a draft. Upstream cursor/plugins#1194 (the source of the #24 fix) is still open. |
| 2026-11-20 | 0.15.46 @ `0b46ec3` | Synced 0.15.45 and 0.15.46. The Gemini panel seat now runs at `gemini-4-neon-xhigh` (arena, poteto-mode, setup-pstack, Claude Code harness doc). Upstream fixed statechart on Windows (cursor/plugins#1292), so the mirror dropped its own #17 patch and took upstream's files as-is. Removed the #17 line from the README fixes list. The rest of the README mirror section is unchanged. statechart tests: the same 10 failures as before, all from this Mac's setup. Upstream's new Windows line-end test passes. Merged #24 as a community fix (watch-pr fork and control-character fix, Cursor's open cursor/plugins#1194 applied unchanged, 56 tests pass) and added its README line. Asked #25 (Devin support) for a smaller version: `docs/harness/devin.md` plus one line in the poteto-mode Harness section. #18 is still a draft. |
| 2026-11-19 | 0.15.44 @ `e58dd04` | Synced. Upstream moved the Gemini panel seat from Gemini 4 Carbon to Gemini 4 Neon in arena, poteto-mode, setup-pstack, the README and the Claude Code harness doc. Took the new model names and setup-pstack's new step that replaces old Gemini panel entries, written as "settings file" like the rest of the mirror. README mirror section unchanged. No new issues or PRs here. #18 is still a draft. New upstream PR cursor/plugins#1287 fixes the CRLF part of #17. The mirror already carries that fix. |
| 2026-11-18 | 0.15.43 | Second check today. No change in pstack. Upstream repo head `35a9094`. No new issues or PRs. #18 is still a draft. #17 has no new replies. Upstream PRs cursor/plugins#1147, #1151, #848 and #1234 are still open. |
| 2026-11-18 | 0.15.43 | No change in pstack. Upstream repo head `93b916d`. New PR #23 adds four new skills (bet-* and bookie), waiting on a decision. Its author opened and closed #21 and #22 themselves. #18 is still a draft. #17 has no new replies. |
| 2026-11-17 | 0.15.43 @ `e1cc031` | Synced. Shorter skill texts, a new `worker.md` for agents that poteto-mode starts, and Opus-first routing capped at xhigh. Upstream deleted the Orchestrate playbook, `check-plan`, and the architect and reflect reference files, so the mirror dropped its edits to them. Kept the #14 and #17 fixes. Updated the README install table: `why` and `architect` no longer need `how`. |
| 2026-11-16 | 0.15.42 | No change in pstack. Upstream repo head `b63c29f`. #18 is still a draft. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-15 | 0.15.42 @ `bf0c7cd` | Synced. New default models (Fable 5.2, Opus 5.5, Gemini 4 Carbon). `how` and `why` are now one file each. Statechart reports SANY errors better. Upstream now gives any unknown model prefix its own family, so the mirror's `gpt-*` line from #19 was dropped in favor of upstream's. Kept the #14 and #17 fixes. 10 statechart tests fail on this Mac, the same on pure upstream. |
| 2026-11-14 | 0.15.36 | No change in pstack. Upstream repo head `3dbd22f`. Closed PR #20, and its author reopened it upstream as cursor/plugins#1234. #18 is still a draft. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-13 | 0.15.36 | No change in pstack. Upstream repo head `3dbd22f`. New PR #20 (`unslop` style rules), waiting on a decision. #18 is still a draft. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-11 | 0.15.36 | No change in pstack. Upstream repo head `5866df5`. New issue #19 (Arena has no GPT model family) and new draft PR #18 (`watch-pr` waits while GitHub computes merge readiness), both waiting on a decision. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-10 | 0.15.36 | No change in pstack. Upstream repo head `de8ee15`. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-09 | 0.15.36 | No change in pstack. Upstream repo head `236e548`. #17 has no new replies. cursor/plugins#1147 is still open. Separately, the sponsor cards now use the new glass Plannotator icon (0b239bb). |
| 2026-11-08 | 0.15.36 | No change in pstack. Upstream repo head `6b03002`, the same as the last check. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-07 | 0.15.36 | No change in pstack. Upstream repo head `6b03002`. #17 has no new replies. cursor/plugins#1147 is still open. |
| 2026-11-06 | 0.15.36 | No change in pstack. Upstream repo head `2776ddd`. #17 has no reply from the reporter. cursor/plugins#1147 is still open. |
| 2026-11-05 | 0.15.36 | No change in pstack. Upstream repo head `2776ddd`. Fixed a gap in the #17 patch: the last line of each chunk kept its `\r`. cursor/plugins#1147 is still open. |
| 2026-11-04 | 0.15.36 | Second check: no change in pstack. Upstream repo head `bb68f23`. Carrying the #17 Windows patch (06572d2), and #17 stays open for items 4 and 5. cursor/plugins#1147 and #1151 are still open. |
| 2026-11-04 | 0.15.36 | No change in pstack. Upstream repo head `bb68f23`. New issue #17: statechart fails on Windows. Upstream tracks it in cursor/plugins#1170, with fix PR #1147 open. |
| 2026-11-03 | 0.15.36 | No change in pstack. Upstream repo head `ae5650f`. |
| 2026-11-02 | 0.15.36 | No change in pstack. Upstream repo head `ae5650f`. |
| 2026-11-01 | 0.15.36 | No change in pstack. Upstream repo head `ae5650f`. |
| 2026-10-31 | 0.15.36 | No change in pstack. Upstream repo head `4dd1d05`. |
| 2026-10-29 | 0.15.36 | No change in pstack. Pulled the README edits made on GitHub. |
| 2026-10-28 | 0.15.36 @ `0f77cd5` | Synced. Upstream deleted the orch scripts and made Orchestrate agentic, so the `--base` fix from #15 was dropped. Interrogate now runs through Arena. |
| 2026-10-27 | 0.15.34 @ `519d36a` | Synced. Statechart rewritten as a TypeScript compiler. |
| 2026-10-25 | 0.15.32 | No change in pstack. |
| 2026-10-24 | 0.15.32 | No change in pstack. |
| 2026-10-23 | 0.15.32 @ `e73df47` | Synced. |
| 2026-10-19 | 0.15.28 @ `d457567` | Synced. |
| 2026-10-15 | 0.15.25 @ `e5136d8` | Synced. |
| 2026-10-13 | 0.15.23 @ `837067b` | Synced. |
| 2026-10-12 | 0.15.20 @ `1b6d44f` | Synced. |
| 2026-10-07 | 0.15.15 @ `ccb5507` | Synced. |
| 2026-10-04 | 0.15.9 @ `e43c7ee` | Synced. |
