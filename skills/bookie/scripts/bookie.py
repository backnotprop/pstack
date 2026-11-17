#!/usr/bin/env python3
"""Run one bet from frame to memo, one stage at a time. Prints JSON for the agent."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bet-record" / "scripts"))

from bet_dialog import MAX_QUESTIONS, Question, frame_questions, memo_questions
from check_bet import DATE, Bet, check_file, parse, strip_fences, table

Entry = dict[str, object]
Option = tuple[str, str]

PRELAUNCH: tuple[Option, ...] = (
    ("Success metric", "The success metric is defined and measured."),
    ("Eval suite", "50 or more eval cases pass at the target rate."),
    ("Pinned versions", "Prompts are in the repository and the model version is pinned."),
    ("Output checks", "Structured output is validated and bad responses are handled."),
    ("Retries", "Retries, timeouts, and a fallback model are in place."),
    ("Tracing", "Each request records inputs, tool calls, output, tokens, and cost."),
    ("Spend caps", "Spend caps and rate limits exist for each user and tenant."),
    ("Injection tests", "Prompt-injection tests ran and side-effect tools need approval."),
    ("Data terms", "Personal data is redacted and provider data terms are reviewed."),
    ("Human path", "A person reviews when needed, and users can reach a person."),
    ("User feedback", "The UI records user feedback."),
    ("Rollback", "A rollback plan and a feature flag are ready."),
)

HANDOFF: tuple[Option, ...] = (
    ("Tests", "Tests cover the behavior that users see."),
    ("Typed interfaces", "The interfaces are typed and documented."),
    ("Eval suite", "The eval suite runs from one command."),
    ("README", "A README says how to run, test, and deploy it."),
)


def choice(
    question: str, header: str, options: tuple[Option, ...], multi: bool = False
) -> Question:
    return {
        "question": question,
        "header": header,
        "multiSelect": multi,
        "options": [{"label": label, "description": text} for label, text in options],
    }


def checklist(question: str, header: str, items: tuple[Option, ...]) -> list[Question]:
    return [
        choice(f"{question} ({i // MAX_QUESTIONS + 1})", header, items[i : i + MAX_QUESTIONS], True)
        for i in range(0, len(items), MAX_QUESTIONS)
    ]


def no_questions(bet: Bet, today: dt.date) -> list[Question]:
    return []


def frame_stage(bet: Bet, today: dt.date) -> list[Question]:
    if not bet.fields.get("Criteria confirmed", ("Open", 0))[0].startswith("Open"):
        return []
    return frame_questions(bet, today)


def build_or_buy(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: the scan is in the record. Which path do you take?",
            "Path",
            (
                ("Build", "Write the thin slice ourselves."),
                ("Buy", "Use a product that the scan found."),
                ("Partner", "Work with a company that the scan found."),
                ("Reuse", "Use a part of the platform we already have."),
            ),
        )
    ]


def scope(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: which rung of the agent ladder does the thin slice start on?",
            "Ladder",
            (
                ("1 Single call", "One prompt and one answer, maybe one tool."),
                ("2 Chain", "Fixed calls in order, with code checks between them."),
                ("3 Router", "A classifier sends each input to its own flow."),
                ("4-6 Agents", "Parallel workers, an orchestrator, or a loop. Needs a reason."),
            ),
        ),
        choice(
            f"{bet.bet_id}: where does a person review the work?",
            "Human step",
            (
                ("Before each write", "A person approves each change to a system of record."),
                ("Before sends", "A person approves only money, sends, and deletes."),
                ("Sample after", "A person reviews a sample of finished work."),
                ("None, read-only", "The slice only reads, so it needs no approval step."),
            ),
        ),
        choice(
            f"{bet.bet_id}: how does the slice reach the system it works on?",
            "Integration",
            (
                ("API or EDI", "The system has an API or EDI feed."),
                ("Email and files", "Work arrives as email, PDF, or spreadsheet."),
                ("Scripted browser", "A stable portal flow, scripted with Playwright."),
                ("Model browser", "Portals vary, so a model drives the browser."),
            ),
        ),
        choice(
            f"{bet.bet_id}: where do the 20 to 50 real examples come from?",
            "Examples",
            (
                ("Customer files", "Emails, documents, and records from a design partner."),
                ("Our own logs", "Tickets or logs that we already hold."),
                ("Public data", "Data that anyone can get."),
                ("Synthetic", "Invented cases. They prove less, so say why."),
            ),
        ),
    ]


def evals(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: which pass rate must the eval set reach before users see it?",
            "Pass rate",
            (
                ("70%", "Acceptable when a person reviews each result."),
                ("80%", "The usual feasibility threshold."),
                ("90%", "Needed when few results get review."),
                ("95%", "Needed when results act with no review."),
            ),
        ),
        choice(
            f"{bet.bet_id}: how many times does each eval case run?",
            "Runs",
            (
                ("1", "Only for code that has no model call."),
                ("3", "The usual minimum to see variation."),
                ("5", "For cases near the threshold."),
            ),
        ),
    ]


def build(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: when do you see the first demo of the thin slice?",
            "Demo",
            tuple(
                ((today + dt.timedelta(days=days)).isoformat(), f"{days} days from today.")
                for days in (3, 5, 7)
            ),
        )
    ]


def harden(bet: Bet, today: dt.date) -> list[Question]:
    return checklist(f"{bet.bet_id}: which pre-launch items are done?", "Pre-launch", PRELAUNCH)


def users(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: who uses the slice first?",
            "First users",
            (
                ("Design partners", "2 or 3 customers who have the problem now."),
                ("Decision maker", "The person who decides go or no-go, as a demo."),
                ("Internal users", "Our own team, before any customer."),
            ),
        ),
        choice(
            f"{bet.bet_id}: what do you ask for at the end of each conversation?",
            "Ask",
            (
                ("Second call", "More time, or an introduction to a colleague."),
                ("Own data", "Use the slice with their own data."),
                ("Letter of intent", "A signed letter of intent or a written price."),
                ("Payment", "A paid pilot or a paid trial."),
            ),
        ),
    ]


def iterate(bet: Bet, today: dt.date) -> list[Question]:
    return [
        choice(
            f"{bet.bet_id}: the week is over. What comes next?",
            "Next week",
            (
                ("Another week", "Review traces, add the failures to the evals, fix the top one."),
                ("Score now", "Score the criteria now, because each one has its evidence."),
            ),
        )
    ]


def memo(bet: Bet, today: dt.date) -> list[Question]:
    return memo_questions(bet, today) + checklist(
        f"{bet.bet_id}: on a go, which handoff items exist now?", "Handoff", HANDOFF
    )


def rows(bet: Bet, section: str) -> list[list[str]]:
    return [cells for _, cells in table(bet.sections.get(section, []))[1]]


def field(bet: Bet, name: str) -> str:
    return bet.fields.get(name, ("Open", 0))[0]


def gate_frame(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    problems = [p for p in check_file(record, today) if bet.bet_id in p]
    if problems:
        return problems[0]
    for name in ("Criteria confirmed", "Decision date"):
        if not DATE.match(field(bet, name).split(" ")[0]):
            return f"{name} is not a date"
    return None


def gate_scan(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    text = " ".join(line for _, line in bet.sections.get("Build-or-buy scan", [])).strip()
    return None if text and "<" not in text else "the Build-or-buy scan section is empty"


def gate_evidence(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    path = entry.get("evidence")
    if not isinstance(path, str):
        return "give --evidence with the path of the stage's output"
    return None if (record.parent / path).exists() else f"evidence path '{path}' does not exist"


def gate_build(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    return None if rows(bet, "Build log") else "the Build log has no row"


def gate_harden(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    answers = entry.get("answers", {})
    assert isinstance(answers, dict)
    missing = [label for label, _ in PRELAUNCH if not answers.get(label)]
    if missing:
        return "answer each pre-launch item as 'done' or 'skip: <reason>': " + ", ".join(missing)
    return None


def gate_users(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    return None if rows(bet, "Customer evidence") else "the Customer evidence table has no row"


def gate_iterate(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    date = field(bet, "Decision date").split(" ")[0]
    if DATE.match(date) and today >= dt.date.fromisoformat(date):
        return None
    if entry.get("note"):
        return None
    return f"the decision date {date} is in the future; give --note with the reason to score early"


def gate_score(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    open_rows = [
        cells[0] for cells in rows(bet, "Kill criteria") if cells[-1] not in ("met", "not met")
    ]
    return f"criteria still open: {', '.join(open_rows)}" if open_rows else None


def gate_memo(bet: Bet, entry: Entry, record: Path, today: dt.date) -> str | None:
    return None if field(bet, "Status").startswith("Decided") else "the Status is not Decided"


Gate = Callable[[Bet, Entry, Path, dt.date], str | None]


@dataclass(frozen=True)
class Stage:
    name: str
    goal: str
    follow: str
    prompts: tuple[int, ...]
    practices: tuple[str, ...]
    questions: Callable[[Bet, dt.date], list[Question]]
    gate: Gate
    skippable: bool = True


STAGES: tuple[Stage, ...] = (
    Stage(
        "frame",
        "Write the core question, the kill criteria, and the decision date.",
        "bet-record frame",
        (1,),
        ("Kill criteria",),
        frame_stage,
        gate_frame,
        False,
    ),
    Stage(
        "build-or-buy",
        "Find what already solves the problem, and pick a path.",
        "bet-diligence for each serious candidate",
        (2, 12),
        ("Integration paths",),
        build_or_buy,
        gate_scan,
    ),
    Stage(
        "scope",
        "Map the job, collect real examples, and pick the thin slice.",
        "",
        (3,),
        ("Scope", "Agent ladder", "Integration paths"),
        scope,
        gate_evidence,
    ),
    Stage(
        "evals",
        "Turn the examples into an eval set with yes/no checks.",
        "",
        (7, 8),
        ("Evals",),
        evals,
        gate_evidence,
    ),
    Stage(
        "build",
        "Build the thin slice and run the eval set on it.",
        "poteto-mode Feature playbook, then bet-record log",
        (4, 5, 6, 9, 10, 11),
        ("Prompts and tools", "Coding agents", "Agent ladder"),
        build,
        gate_build,
    ),
    Stage(
        "harden",
        "Make the slice safe to put in front of users.",
        "",
        (),
        ("Production", "Safety"),
        harden,
        gate_harden,
    ),
    Stage(
        "users",
        "Put the slice in front of real users and log what they do.",
        "bet-discovery",
        (15,),
        ("Kill criteria",),
        users,
        gate_users,
    ),
    Stage(
        "iterate",
        "Each week, turn failures into eval cases and fix the top one.",
        "bet-record log",
        (7, 11),
        ("Evals", "Anti-patterns"),
        iterate,
        gate_iterate,
    ),
    Stage(
        "score",
        "Set each criterion to met or not met from fresh evidence.",
        "bet-record score",
        (13,),
        ("Kill criteria",),
        no_questions,
        gate_score,
        False,
    ),
    Stage(
        "memo",
        "Write the go, no-go, or pivot memo and record the decision.",
        "bet-record memo",
        (14,),
        ("Memo items", "Handoff"),
        memo,
        gate_memo,
        False,
    ),
)
BY_NAME = {stage.name: stage for stage in STAGES}


def progress_path(record: Path, bet_id: str) -> Path:
    return record.parent / "bookie" / f"{bet_id}.json"


def load_progress(record: Path, bet_id: str) -> dict[str, Entry]:
    path = progress_path(record, bet_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def save_progress(record: Path, bet_id: str, progress: dict[str, Entry]) -> None:
    path = progress_path(record, bet_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(progress, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def find_bet(record: Path, bet_id: str) -> Bet | None:
    if not record.exists():
        return None
    lines = strip_fences(record.read_text(encoding="utf-8").splitlines())
    return next((bet for bet in parse(lines) if bet.bet_id == bet_id), None)


def current(progress: dict[str, Entry]) -> Stage | None:
    return next(
        (s for s in STAGES if progress.get(s.name, {}).get("status") not in ("done", "skipped")),
        None,
    )


def describe(
    stage: Stage, bet: Bet | None, entry: Entry, record: Path, today: dt.date
) -> dict[str, object]:
    if bet is None:
        gate, questions = f"{record} has no section for this bet", []
    else:
        gate = stage.gate(bet, entry, record, today)
        questions = stage.questions(bet, today)
    return {
        "stage": stage.name,
        "number": f"{STAGES.index(stage) + 1} of {len(STAGES)}",
        "goal": stage.goal,
        "follow": stage.follow,
        "prompts": list(stage.prompts),
        "practices": list(stage.practices),
        "gate": gate or "passed",
        "calls": [
            {"questions": questions[i : i + MAX_QUESTIONS]}
            for i in range(0, len(questions), MAX_QUESTIONS)
        ],
    }


def next_stage(record: Path, bet_id: str, today: dt.date) -> dict[str, object]:
    progress = load_progress(record, bet_id)
    stage = current(progress)
    if stage is None:
        return {"stage": None, "result": "every stage is done or skipped"}
    return describe(stage, find_bet(record, bet_id), progress.get(stage.name, {}), record, today)


def status(record: Path, bet_id: str) -> list[dict[str, object]]:
    progress = load_progress(record, bet_id)
    now = current(progress)
    return [
        {
            "stage": s.name,
            "status": "current"
            if s is now
            else str(progress.get(s.name, {}).get("status", "open")),
            "date": progress.get(s.name, {}).get("date"),
        }
        for s in STAGES
    ]


def finish(
    record: Path,
    bet_id: str,
    name: str,
    today: dt.date,
    *,
    evidence: str | None = None,
    answers: dict[str, str] | None = None,
    note: str | None = None,
    skip: bool = False,
) -> str:
    progress = load_progress(record, bet_id)
    stage = current(progress)
    if stage is None or stage.name != name:
        raise SystemExit(
            f"{name} is not the current stage; the current stage is {stage and stage.name}"
        )
    if skip and not stage.skippable:
        raise SystemExit(f"{name} cannot be skipped")
    if skip and not note:
        raise SystemExit("a skip needs --note with the reason")
    entry = dict(progress.get(name, {}))
    if evidence:
        entry["evidence"] = evidence
    if answers:
        merged = dict(entry.get("answers", {}))  # type: ignore[arg-type]
        merged.update(answers)
        entry["answers"] = merged
    if note:
        entry["note"] = note
    if not skip:
        bet = find_bet(record, bet_id)
        problem = (
            f"{record} has no section for {bet_id}"
            if bet is None
            else stage.gate(bet, entry, record, today)
        )
        if problem:
            progress[name] = entry
            save_progress(record, bet_id, progress)
            raise SystemExit(f"{name} gate: {problem}")
    entry.update(status="skipped" if skip else "done", date=today.isoformat())
    progress[name] = entry
    save_progress(record, bet_id, progress)
    following = current(progress)
    return following.name if following else "none"


def parse_answers(pairs: list[str]) -> dict[str, str]:
    answers = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise SystemExit(f"--answer needs LABEL=VALUE, got '{pair}'")
        answers[key.strip()] = value.strip()
    return answers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("bet_id")
    parser.add_argument("command", choices=("next", "status", "done", "skip"))
    parser.add_argument("stage", nargs="?", choices=sorted(BY_NAME))
    parser.add_argument("--evidence")
    parser.add_argument("--answer", action="append", default=[])
    parser.add_argument("--note")
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    if args.command == "next":
        print(json.dumps(next_stage(args.record, args.bet_id, args.today), indent=1))
    elif args.command == "status":
        print(json.dumps(status(args.record, args.bet_id), indent=1))
    else:
        if not args.stage:
            parser.error(f"{args.command} needs a stage")
        following = finish(
            args.record,
            args.bet_id,
            args.stage,
            args.today,
            evidence=args.evidence,
            answers=parse_answers(args.answer),
            note=args.note,
            skip=args.command == "skip",
        )
        print(f"{args.stage} {args.command}; next stage: {following}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
