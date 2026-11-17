---
name: bet-discovery
description: "Plan and log customer discovery for a bet: pick who to talk to, write questions about past behavior, run or prepare the interview, and log what people did as customer evidence that the kill criteria can count. Use for /bet-discovery, 'customer interviews', 'talk to users', 'log this call', 'what did the user say', or when a bet reaches users."
disable-model-invocation: true
---

# Bet discovery

Discovery finds out what people do, not what they say they would do. Only what people do counts as evidence for a kill criterion. A compliment is not usage, and a promise is not payment.

The record and its format belong to **bet-record**. This skill fills its **Customer evidence** table. Find the record as **bet-record** says.

## Plan

1. Read the bet's core question and kill criteria. Name the criteria that need people: usually pull, use, and payment.
2. Name who to talk to: the people who have the problem now and pay to solve it today. Write each one as a role and a letter, such as "agency owner A". Never write a real name, an email, or a company name in the record.
3. Write the questions from [`references/interview-guide.md`](references/interview-guide.md). Choose at most five. Each one asks about a past event, not a future wish.
4. Name the next step that you will ask for at the end, from the commitment ladder in the guide. A conversation that ends with no ask gives no evidence.

## Log

After each conversation or each sign of use, add one row to the **Customer evidence** table:

| Cell | What goes in it |
| --- | --- |
| Date | The day of the event, YYYY-MM-DD |
| Who | Role and letter |
| Kind | `interview`, `usage`, `commitment`, or `payment` |
| What they did | The act, in the past tense. "Added 4 sites and kept them 14 days", not "Liked the page". |
| Evidence | A pointer that resolves: database rows and the query output path, notes path, a signed paper, a payment record |
| Criterion | The kill criterion number that the row counts for, or `-` |

Keep the full notes in a file beside the record and point at it. The table holds one line for each event.

Put an opinion only in the notes, never in **What they did**. An `interview` row counts for no criterion that needs use or payment.

Run the **bet-record** checker after each edit. It checks this table.

## Read the evidence

When the bet is scored, count only rows of the kind that the criterion names. Three people who said yes are zero people who used it. If the rows contradict the bet, say so first in the next reply, not last.

## Rules

- Do not pitch during an interview. The goal is facts about the past.
- Do not lead. "How do you check your sites today?" is fine. "Would you use a tool that checks your sites?" is not.
- Ask the person before you record a call, and keep recordings out of git.
