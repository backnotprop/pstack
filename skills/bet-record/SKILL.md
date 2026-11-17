---
name: bet-record
description: "Keep a product bet honest: frame its core question, kill criteria, and decision date before code; log one row per verified unit; score the criteria from evidence; write the go, no-go, or pivot memo on the decision date. Use for /bet-record, 'new bet', 'log this to the bet', 'score the bet', 'write the go/no-go memo', or after a poteto-mode unit is verified on a project that has a bet record."
disable-model-invocation: true
---

# Bet record

A bet is a product idea that gets a fast build, real users, and a decision. The record decides whether to keep building. **poteto-mode** decides how to build each unit. The kill criteria connect the two: each criterion is a done check that a unit must prove.

## Find the record

The project `CLAUDE.md` names the record file. With no name there, use `docs/bet-process.md`. One file holds every bet, one `## BET-NNN: <name>` section each. Start a new section from [`references/bet-record-template.md`](references/bet-record-template.md).

Run `python3 .claude/skills/bet-record/scripts/check_bet.py <record>` after every edit. Fix each line it prints before you reply. The script owns the format rules, so this file does not repeat them.

## Pick the step

The invocation names the step. With no name, run `check` and say which step the record needs next.

### frame

1. Write the core question as one question that a build can answer.
2. Propose 3 to 6 kill criteria. Give each one a number as its threshold and name the evidence that counts. Prefer evidence that a command prints over evidence that a person counts.
3. Propose a decision date 2 to 4 weeks after the build starts.
4. Write the proposals into the record with **Criteria confirmed** at `Open`. Then run the operator dialog for `frame`. Criteria and the date are product calls, so only the operator confirms them.
5. Apply the answers. `Confirm` keeps the row. `Drop` deletes the row. Free text replaces the threshold with the operator's words. Write today's date in **Criteria confirmed** and the chosen date in **Decision date**. If the operator dropped every criterion, keep `Open` and propose new criteria.

### log

Add one build log row for each verified unit, after the verification and not before. The evidence cell holds a pointer that resolves: a commit SHA, a file path, a PR, or a saved output path. When a unit moves a kill criterion, name the criterion number in the unit cell.

Long runs keep their full decision trail in the **show-me-your-work** skill. The build log holds one summary row per unit and points at that trail.

### score

For each criterion, read its evidence and set the result to `met`, `not met`, or `open`. Run the command that produces the evidence rather than trust an earlier number, per the **prove-it-works** principle skill. Never change a criterion, a threshold, or the decision date while you score. That needs the operator.

### memo

Write the memo on the decision date, or earlier when every criterion is decided. Fill the eight memo items from the build log and the criteria results only. Lead with the recommendation. A missed criterion is a no-go or a pivot. A pivot names the new evidence and gets a new bet with its own criteria. Write under **technical-writing**, then **unslop**. Then run the operator dialog for `memo`. Set the status to `Decided: go`, `Decided: no-go`, or `Decided: pivot` from the answer. If the answer differs from the recommendation, keep the recommendation in the memo and add the operator's decision and reason.

## Operator dialog

Ask the operator through your structured-question tool (`AskUserQuestion` in Claude Code). Do not ask in free chat, and do not write the questions by hand. Build them from the record:

```sh
python3 .claude/skills/bet-record/scripts/bet_dialog.py <record> BET-NNN frame
python3 .claude/skills/bet-record/scripts/bet_dialog.py <record> BET-NNN memo
```

The script prints a JSON list. Each item is one question-tool call that holds at most 4 questions. Send the calls in order and send each item's `questions` unchanged. The tool adds a free-text choice to each question, so the operator can write a new threshold or another date. A question with no answer stays `Open`. Under a full-autonomy grant, still run the dialog, because these calls belong to the operator.

## Rules

- Criteria and the decision date come before the first line of code. A bet in `Building` with no confirmed criteria is a check failure, not a warning.
- Do not move the decision date. Do not soften a criterion to keep a bet alive.
- Every result needs evidence. A compliment is not usage, and a promise is not payment.
- The **bet-omni** skill runs these steps with the other bet skills, in stage order from frame to memo.
- The **bet-discovery** skill fills **Customer evidence**. The **bet-diligence** skill writes the memo for the build-or-buy scan and for any outside dependency of the bet.
- When the record copies text from an outside source, follow the record's anonymization rules.
