---
name: bet-diligence
description: "Review the code, the team, and the market of a company, product, repository, or dependency that a bet could rely on, and write a diligence memo with evidence for each finding. Grow a reusable checklist with each review. Use for /bet-diligence, 'diligence on X', 'review this codebase before we build on it', 'can we rely on library X', 'should we buy or partner with X', or the build-or-buy scan of a bet."
disable-model-invocation: true
---

# Bet diligence

Diligence answers one question about a subject: can a bet rely on it? The memo gives a recommendation and the evidence for it. The checklist makes the next review faster.

## Start

1. Write the question as one sentence, for example "Can BET-001 rely on h11 for its HTTPS checks?" Name the bet when there is one.
2. Find the bet record from the project `CLAUDE.md`, as for **bet-record**. Call its folder the record folder.
3. Copy [`references/diligence-memo-template.md`](references/diligence-memo-template.md) to `<record folder>/diligence/<subject>.md`. The subject name is lowercase, with hyphens for spaces.
4. Save command output and API responses to `<record folder>/evidence/<subject>/`. Evidence cells point there.
5. Read [`references/checklist.md`](references/checklist.md). Each item that applies becomes a check. An item that does not apply goes under **Not checked** with the reason.

## Review

Pick the methods for the kind of subject. Run independent areas in parallel subagents when the subject is large and you are not a subagent already.

| Area | Source repository | Installed dependency | Product or company |
| --- | --- | --- | --- |
| Code | Clone it to a scratch folder. Build it and run its tests there. | Read the installed source. Run the project's own tests that use it. | Read the public docs and API reference. |
| Team | Read the git history | Use the public package registry and forge APIs, read-only | Use public sources: site, filings, job posts |
| Market | Alternatives that meet the same need | Alternative libraries, and what a switch costs | Competing products, with price and source |

For the code, run the **how** skill on the parts that the bet uses. Run the **blast-radius** skill when the bet would change the subject. Use the `security-audit` skill in guidance mode when it is available.

A fact that only a run can prove, when a run is out of scope, goes under **Not checked** with the command that would prove it.

Each finding is one table row with evidence: a `file:line`, an output path, a commit, or a URL with its UTC access date. Write `\|` for a pipe inside a cell. A finding with no evidence is not a finding.

Severity is `high` when it can stop the bet, `medium` when it costs real work, `low` when it is a nuisance, and `info` for a neutral fact.

## Decide

Lead with the recommendation: `Support`, `Support with conditions`, or `Do not support`. A `high` finding rules out a plain `Support`. Give the conditions as a numbered list, each with the finding numbers it answers. Name each `high` and `medium` finding in a condition or under **Risks**. Write under **technical-writing**, then **unslop**.

Run `python3 .claude/skills/bet-diligence/scripts/check_diligence.py <memo>` after each edit. Fix each line it prints before you reply.

When the subject is part of a bet:

- Add one line to the bet's **Build-or-buy scan**: the subject, the recommendation, and the memo path.
- Add one build log row with the memo path, through the **bet-record** `log` step. A finished memo is a verified unit.

## Grow the checklist

After the memo passes its check, add each new kind of check that the review needed to `references/checklist.md`, one line each. The checklist holds kinds of checks, never facts about one subject. If the operator forbids changes to skill files, list the new lines in your reply instead.

## Rules

- Write people as roles, such as "the top author", never as names or logins.
- Never copy secrets or private customer data into the memo.
- Run outside code only in a scratch folder, never from inside the project, and never with credentials.
