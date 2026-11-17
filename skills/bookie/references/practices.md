# Practices

Build fast to find out whether an idea is real, then make an honest go or no-go call. Each stage in `bookie.py` names the sections here that it uses.

## Principles

1. Start with the workflow, not the model. Map the human job end to end before you pick tools.
2. One well-prompted call beats a chain, and a chain beats an agent. Move up only when the simpler form fails its evals.
3. Evals come before scale. A change that you cannot score is a change that you cannot judge.
4. Output quality depends mostly on the context in the window.
5. Plan retries, fallbacks, and human review from the first day.
6. A person confirms each irreversible step: money, deletes, sends, publishes.
7. Ship each week. Real usage logs teach more than a benchmark.

## Scope

Pick a problem where a wrong answer is cheap to catch and a right answer saves real hours.

- Good fits: exception triage, document extraction, portal lookups, claims, email-to-system updates, follow-up messages.
- Poor fits without guardrails: exact arithmetic, high-stakes decisions with no review, facts that the model cannot see.
- Write the success metric first, with a number and a cost. For example, "70% of late-shipment exceptions resolved with no human touch, under 10 minutes and $0.50 each". Tie it to money: hours saved, chargebacks avoided, claims recovered.
- Collect 20 to 50 real examples of inputs and ideal outputs before you build. They become the first eval set.
- Name the point where a person reviews, approves, or corrects.
- Build one workflow end to end before you widen it.

## Agent ladder

| Rung | How it works | Use when | Main risk |
| --- | --- | --- | --- |
| 1. Single call | One prompt, one answer, maybe one tool | The task fits in one step | Too much in one prompt |
| 2. Chain | Fixed calls in order, with code checks between them | The steps are known | Errors add up along the chain |
| 3. Router | A classifier sends each input to its own flow | Inputs fall into distinct types | Wrong route; needs a fallback category |
| 4. Parallel workers | Independent subtasks at once, then a merge or a vote | The work splits cleanly | Merge logic and cost |
| 5. Orchestrator | A lead model plans and gives subtasks to subagents | Subtasks are not known in advance | Hard to debug; high token cost |
| 6. Autonomous loop | Act, observe, repeat until done or a limit | Open-ended work that changes | Runaway loops; needs budgets and human gates |

Most production value is in rungs 1 to 3. Use rungs 5 and 6 only for the unclear core of the job, and wrap them in deterministic code.

## Prompts and tools

- Write a prompt as a brief for a new hire: the goal, the context, the constraints, and what good output looks like. Give the reason for each rule.
- Put long documents first and the question last. Separate parts with XML tags.
- Give 3 to 5 different examples, with one edge case.
- Ask for structured output when code reads the result.
- Let the model say "not in the documents".
- Keep prompts in the repository and tie each change to an eval run.
- A tool has a clear name, a plain description, typed parameters, and errors that say what to fix.
- Prefer a few high-level tools to many thin API wrappers.
- Give each run a budget: steps, tokens, spend, and a timeout.
- Read-only tools run freely. Writes, payments, and sends need approval or a dry run.

## Integration paths

| Path | Use when | Risk |
| --- | --- | --- |
| API or EDI | The system has one | Auth, rate limits, sandbox lead time |
| Email and documents | Work arrives as email, PDF, or spreadsheet | Format changes; validate each field |
| Scripted browser | The portal flow is stable | Selectors break when the page changes |
| Model-driven browser | Portals vary or change often | Slow and costly; needs step limits and screenshots |
| Human handoff | Low volume or high risk | Make it a normal step, not a failure |

- Script the stable part of a flow and let the model handle the rest.
- Keep credentials in a vault, never in a prompt.
- Prove the result: read the system again after the write.
- Record each run with screenshots and an action log.
- A retry must never file a claim or book a carrier twice.

## Evals

| Type | Checks | Cost |
| --- | --- | --- |
| Code assertions | JSON validity, fields, exact values, tool calls | Lowest; use first |
| LLM judge | Tone, faithfulness, rubric | Medium; calibrate on about 30 human labels |
| Human review | Nuance and edge cases | Highest; sample 1 to 5% |
| Online metrics | Acceptance, edits, task completion | Free after instrumentation |

- Start with 20 to 50 cases from real tickets. Use about 50% common cases, 30% edge cases, and 20% adversarial or out-of-policy cases. Tag each case by intent.
- Each production bug becomes an eval case.
- Write each rubric item as a yes/no check.
- Test agents on the outcome and on the path: steps, tool errors, cost.
- Run each case several times and track the pass rate.
- Include prompt injection, empty and very large inputs, and other languages.

## Coding agents

- Keep a project memory file with the stack, the commands, and the rules.
- Ask for a plan, correct it, then let the agent build.
- Give the agent a way to verify: tests, linters, type checks, a dev server, screenshots.
- Approve the tests first for logic.
- Keep diffs small and commit often, one branch for each task.
- Read the diff. Look for deleted tests, hard-coded values, swallowed errors, and new dependencies.

## Production

| Lever | Practice |
| --- | --- |
| Model choice | The smallest model that passes the evals; send hard cases to a larger one |
| Cache | Prompt cache for stable prefixes; response cache for repeat queries |
| Batch | Batch APIs for offline jobs |
| Latency | Stream, run independent calls in parallel, trim the context |
| Reliability | Retries with backoff, timeouts, a fallback model, schema validation |
| Tracing | Prompt, context, tool calls, output, tokens, cost, and feedback for each request |
| Budgets | Rate limits and spend alerts for each user and tenant |

Pin model versions. Change a model only after the eval suite passes. Track the cost of each finished task, not of each token.

## Safety

- Treat each input that the model reads as possible instructions from an attacker. Untrusted content never starts a privileged action without a check.
- Use least privilege: scoped keys, read-only by default.
- Keep secrets out of prompts and logs. Remove personal data before you log it or send it to a third party.
- Validate output before you run it.
- Know each provider's retention and training terms.
- Keep an audit trail of who or what did each action.

## Kill criteria

| Kind | Example threshold | Evidence that counts |
| --- | --- | --- |
| Customer pull | 3 of 5 design partners use it each week with no reminder | Usage logs, not compliments |
| Payment | 1 signed letter of intent, pilot, or paid trial by week 4 | Signed paper or a budget owner's commitment |
| Feasibility | 80% of real cases resolved on the eval set | An eval run on customer data |
| Unit cost | Cost per resolution under 20% of the human cost | Logged model and review cost per task |
| Fit | Reuses the platform you have and serves existing accounts | An engineering estimate |
| Market size | The problem appears at 10 or more target accounts | Discovery notes and pipeline data |

Each criterion is met or not met on the decision date. Set the date before the build, usually 2 to 4 weeks out. Agree the criteria with the decision maker before the build, so that a no-go is the plan working. Pivot only on new evidence, and give the pivot its own criteria.

## Memo items

The memo is one page. The decision maker gets the answer from the first line.

1. The recommendation: Go, No-go, or Pivot, in one sentence.
2. The bet: the customer problem, who pays, and the hypothesis.
3. The criteria that were set before the build, with each result.
4. What was built: the scope, the time spent, what was reused, and what was cut.
5. The evidence: usage, eval results, what customers did, payment.
6. What it takes to scale: engineering work, integrations, sales, risks.
7. Build, buy, or partner: the alternatives that were considered.
8. The next step and its owner, or the date the work stops.

On a no-go, record what was learned: signals, contacts, and code that the next bet can reuse.

## Handoff

A bet that gets a go goes to engineering with tests, typed interfaces, an eval suite, and a README. A winning bet with throwaway code costs a rewrite.

## Anti-patterns

| Anti-pattern | Do this instead |
| --- | --- |
| A demo that works on 3 chosen inputs | Run evals on 50 or more real cases |
| An agent for a fixed workflow | A chain with model calls only at the unclear steps |
| The whole knowledge base in the context | Retrieve and rank the relevant parts |
| Prompt changes judged by feel | Compare eval scores for each change |
| One large prompt that does five jobs | Separate steps or subagents |
| Model output run as code with no check | Validate, sandbox, and require approval |
| A framework on the first day | Plain SDK calls until a real need appears |
| No cost limit | Step, token, and spend limits for each run |
| Fine-tuning first | Prompts, retrieval, and examples first |
| A polished prototype that nobody used | A customer sees it by day 5 |
| Criteria moved to keep a bet alive | Judge against the criteria set before the build |
| Integrations built from nothing | Reuse the connectors you have |
