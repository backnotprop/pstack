# Prompts

Each stage in `bookie.py` names the prompts it uses by number. Replace each `<placeholder>` before you use a prompt. Use a prompt on yourself, give it to a subagent, or show it to the operator to use elsewhere.

## 1. Frame the bet (hour 0)

```text
I am about to build a prototype for this bet:
<one paragraph: the customer problem, who has it, what they do today>

Write:
1. The core question, as one question that a 2-week build can answer.
2. 3 to 5 kill criteria. Give each one a number as its threshold and the evidence
   that counts. Usage logs, signed paper, and eval runs count. Compliments do not.
3. A decision date 2 to 4 weeks from <start date>.
Do not write code. Mark each criterion that only the CEO can confirm.
```

## 2. Build-or-buy scan (1 hour)

```text
List the products, open-source projects, and parts of our own platform that
already solve <the workflow>. For each one, give: what it does, the price with its
source URL and the date you read it, and what it does not do for our case.
End with one line: build, buy, partner, or reuse, and the reason.
If you cannot find a price, write "unknown". Do not guess.
```

## 3. Scope the thin slice

```text
Here are 20 real examples of <exception type>, with the ideal resolution for each:
<paste examples or point to the folder>

Map the human job end to end, step by step. For each step, say whether it is
deterministic code, one model call, or a human review. Then propose the smallest
vertical slice that resolves one exception end to end. Name the success metric,
for example "70% resolved with no human touch, under 10 minutes and $0.50 each".
```

## 4. Extraction prompt (rung 1, single call)

```text
<documents>
<email>{{email_body}}</email>
<attachment name="{{file_name}}">{{attachment_text}}</attachment>
</documents>

You read carrier emails for a freight operations team. The team uses your output
to update the TMS, so a wrong value causes a wrong customer notice.

Extract the carrier name, the PRO number, the original ETA, and the new ETA.
Use only values that appear in the documents. If a value is missing, use null.
Do not compute dates. Return JSON that matches this schema:
{"carrier": str|null, "pro_number": str|null, "original_eta": "YYYY-MM-DD"|null,
 "new_eta": "YYYY-MM-DD"|null, "evidence": [str]}
Put the exact source sentence for each value in "evidence".
```

## 5. Router prompt (rung 3)

```text
Classify this inbound email into exactly one category:
delay, short_ship, damage_claim, order_change, other.

<examples>
<example category="short_ship">"We received 40 cases, PO says 48."</example>
<example category="order_change">"Please push delivery to Thursday."</example>
<example category="other">"Invoice attached for October."</example>
</examples>

Use "other" when no category fits or the email has two different requests.
Return {"category": ..., "reason": "<one sentence>"}.

<email>{{email_body}}</email>
```

## 6. Tool description (agents)

```text
Name: reschedule_delivery
Description: Move one open delivery appointment to a new date at the same dock.
Use this only after the customer confirms the new date in writing. It does not
change the carrier or the PO. Returns the new appointment ID, or an error that
says what to fix, for example "date must be YYYY-MM-DD and on a business day".
Parameters:
  appointment_id (string, for example "APT-20431")
  new_date (string, YYYY-MM-DD)
  dry_run (boolean, default true; set false only after approval)
```

## 7. Eval set from real tickets

```text
Here are <N> real tickets with their resolutions: <folder or paste>.
Build an eval set of 30 cases: about 50% common, 30% edge cases, 20% adversarial
or out of policy. For each case give: id, intent tag, input, the state the agent
can see, pass criteria as yes/no checks, and the grader (code or LLM judge).
Prefer a code grader whenever the check is a field, a tool call, or a number.
Do not invent order numbers or tracking data that are not in the tickets.
```

## 8. LLM-as-judge rubric

```text
You grade one support reply. Answer each check with yes or no and one sentence
of evidence quoted from the reply.

1. Every date and tracking number in the reply appears in the tool results.
2. The reply offers only actions that the written policy allows.
3. The reply answers each issue the customer raised.
4. The reply offers a human when the customer asks for one or is angry.

<policy>{{policy}}</policy>
<tool_results>{{tool_results}}</tool_results>
<reply>{{reply}}</reply>

Return {"checks": [{"id": 1, "pass": true, "evidence": "..."}, ...]}.
```

Calibrate the judge on about 30 replies that a person labeled before you trust its scores.

## 9. Coding agent: plan first

```text
Read CLAUDE.md and <the relevant files>. Do not edit yet.
Goal: <one sentence, with the user and the outcome>.
Give me a plan: the data shape first, then the files you will change, the tests
that will prove it works, and what you will not do. Wait for my answer.
```

## 10. Coding agent: test first, then implement

```text
Write failing tests for <behavior> from these cases: <cases>. Test what a caller
can observe, not internal calls. Show me the tests and stop.
```

```text
The tests are approved. Make them pass with the smallest change. Run the tests,
the linter, and the type check, and show the output. Do not change the tests.
Do not add a dependency without asking.
```

## 11. Review the agent's diff

```text
Review this diff as a skeptical senior engineer: <diff or branch>.
Look for deleted or weakened tests, hard-coded values, swallowed errors, new
dependencies, secrets, and side effects with no approval gate.
Give one line for each finding: file:line, the problem, the fix.
```

## 12. Technical diligence

```text
Question: can <bet> rely on <target or library> for <use>?
Review the code, the team, and the market. For each finding give the evidence
(file:line, command output, commit, or URL with the date) and a severity:
high (it can stop the bet), medium (real work), low, or info.
A finding with no evidence is not a finding.
End with: Support, Support with conditions (numbered, each naming its findings),
or Do not support. Write people as roles, not names.
```

## 13. Score the kill criteria

```text
Here are the kill criteria and the evidence: <criteria>, <logs, eval runs, LOIs>.
Run the command that produces each number again. Do not trust earlier numbers.
For each criterion, write met, not met, or open, with the evidence pointer.
Do not change a criterion, a threshold, or the decision date.
```

## 14. Go/no-go memo

```text
Write a one-page go/no-go memo from the build log and the criteria results only.
Follow the eight memo items in practices.md. Put the recommendation in the first
sentence. A missed criterion is a no-go or a pivot. A pivot names the new evidence
and gets its own new criteria. Quote no customer praise as evidence.
```

## 15. Customer discovery questions

```text
Write 5 interview questions for <role> about <problem>. Ask only about past
behavior: the last time it happened, what it cost, what they use and pay today.
Do not name our product, and do not ask "would you use" or "how much would you
pay". End with an ask for the next step: a second call, an introduction, use with
their own data, a letter of intent, or payment.
```
