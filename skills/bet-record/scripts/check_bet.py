#!/usr/bin/env python3
"""Check a bet record file. Prints one line per problem and exits 1 if any."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

STATUSES = ("Framing", "Building", "With users", "Decided: go", "Decided: no-go", "Decided: pivot")
RESULTS = ("met", "not met", "open")
FIELDS = ("Core question", "Status", "Criteria confirmed", "Decision date")
SUBSECTIONS = (
    "Kill criteria",
    "Build-or-buy scan",
    "Build log",
    "Customer evidence",
    "Decision memo",
)
CRITERIA_HEADER = ["#", "Criterion", "Threshold", "Evidence that counts", "Result"]
LOG_HEADER = ["Date", "Unit", "Evidence"]
EVIDENCE_HEADER = ["Date", "Who", "Kind", "What they did", "Evidence", "Criterion"]
EVIDENCE_KINDS = ("interview", "usage", "commitment", "payment")

BET_HEADING = re.compile(r"^## (BET-\d{3}): (\S.*)$")
FIELD_LINE = re.compile(r"^\*\*([^*]+)\.\*\* ?(.*)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
PLACEHOLDER = re.compile(r"<[^>]+>")


@dataclass
class Bet:
    bet_id: str
    line: int
    fields: dict[str, tuple[str, int]] = field(default_factory=dict)
    sections: dict[str, list[tuple[int, str]]] = field(default_factory=dict)


def strip_fences(lines: list[str]) -> list[tuple[int, str]]:
    kept, inside = [], False
    for number, text in enumerate(lines, start=1):
        if text.startswith("```"):
            inside = not inside
            continue
        if not inside:
            kept.append((number, text))
    return kept


def parse(lines: list[tuple[int, str]]) -> list[Bet]:
    bets: list[Bet] = []
    current: Bet | None = None
    section: str | None = None
    for number, text in lines:
        if text.startswith("## "):
            match = BET_HEADING.match(text)
            current = Bet(match.group(1), number) if match else None
            if current:
                bets.append(current)
            section = None
            continue
        if current is None:
            continue
        if text.startswith("### "):
            section = text[4:].strip()
            current.sections[section] = []
            continue
        if section is None:
            match = FIELD_LINE.match(text)
            if match:
                current.fields[match.group(1)] = (match.group(2).strip(), number)
        else:
            current.sections[section].append((number, text))
    return bets


def table(rows: list[tuple[int, str]]) -> tuple[list[str] | None, list[tuple[int, list[str]]]]:
    cells = [
        (n, [c.strip() for c in t.strip().strip("|").split("|")])
        for n, t in rows
        if t.strip().startswith("|")
    ]
    if not cells:
        return None, []
    return cells[0][1], [c for c in cells[1:] if not all(set(x) <= set("-: ") for x in c[1])]


def first_word_value(value: str) -> str:
    for status in sorted(STATUSES, key=len, reverse=True):
        if value == status or value.startswith(status + "."):
            return status
    return value.split(".")[0].strip()


def check_bet(bet: Bet, today: dt.date, path: str) -> list[str]:
    problems: list[str] = []

    def report(line: int, message: str) -> None:
        problems.append(f"{path}:{line}: {bet.bet_id}: {message}")

    for name in FIELDS:
        if name not in bet.fields:
            report(bet.line, f"missing field '**{name}.**'")
    for name in SUBSECTIONS:
        if name not in bet.sections:
            report(bet.line, f"missing section '### {name}'")
    if problems:
        return problems

    status_text, status_line = bet.fields["Status"]
    status = first_word_value(status_text)
    if status not in STATUSES:
        report(status_line, f"status '{status_text}' is not one of: {', '.join(STATUSES)}")

    dates: dict[str, dt.date | None] = {}
    for name in ("Criteria confirmed", "Decision date"):
        value, line = bet.fields[name]
        token = value.split(" ")[0].rstrip(".")
        if DATE.match(token):
            dates[name] = dt.date.fromisoformat(token)
        elif token == "Open":
            dates[name] = None
        else:
            report(line, f"'{name}' must be YYYY-MM-DD or Open, not '{value}'")
            dates[name] = None

    past_framing = status in STATUSES and status != "Framing"
    if past_framing:
        for name in ("Criteria confirmed", "Decision date"):
            if dates[name] is None:
                report(
                    bet.fields[name][1],
                    f"status is '{status}', so '{name}' must be a date set before the build starts",
                )
    confirmed, decision = dates["Criteria confirmed"], dates["Decision date"]
    if confirmed and decision and decision < confirmed:
        report(
            bet.fields["Decision date"][1],
            "decision date is before the date the criteria were confirmed",
        )
    if decision and decision < today and not status.startswith("Decided"):
        report(
            bet.fields["Decision date"][1], f"decision date {decision} has passed; write the memo"
        )

    header, rows = table(bet.sections["Kill criteria"])
    if header != CRITERIA_HEADER:
        report(bet.line, f"kill criteria table header must be: | {' | '.join(CRITERIA_HEADER)} |")
    elif not rows:
        report(bet.line, "kill criteria table has no rows")
    results = []
    numbers = {cells[0] for _, cells in rows} if header == CRITERIA_HEADER else set()
    for line, cells in rows if header == CRITERIA_HEADER else []:
        if len(cells) != len(CRITERIA_HEADER):
            report(line, "kill criteria row has the wrong number of cells")
            continue
        if not cells[2]:
            report(line, "kill criterion has no threshold")
        if past_framing and any(PLACEHOLDER.search(c) for c in cells):
            report(line, "kill criterion still has a <placeholder>")
        result = cells[4].lower()
        results.append(result)
        if result not in RESULTS:
            report(line, f"result '{cells[4]}' is not one of: {', '.join(RESULTS)}")

    header, rows = table(bet.sections["Build log"])
    if header != LOG_HEADER:
        report(bet.line, f"build log table header must be: | {' | '.join(LOG_HEADER)} |")
    for line, cells in rows if header == LOG_HEADER else []:
        if len(cells) != len(LOG_HEADER) or not DATE.match(cells[0]):
            report(line, "build log row must start with a YYYY-MM-DD date and have 3 cells")
        elif not cells[1] or not cells[2]:
            report(line, "build log row needs a unit and evidence")

    header, rows = table(bet.sections["Customer evidence"])
    if header is not None and header != EVIDENCE_HEADER:
        report(
            bet.line, f"customer evidence table header must be: | {' | '.join(EVIDENCE_HEADER)} |"
        )
    elif header is None and status == "With users":
        report(status_line, "a bet with users needs a customer evidence table with rows")
    for line, cells in rows if header == EVIDENCE_HEADER else []:
        if len(cells) != len(EVIDENCE_HEADER) or not DATE.match(cells[0]):
            report(line, "customer evidence row must start with a YYYY-MM-DD date and have 6 cells")
            continue
        _, who, kind, did, evidence, criterion = cells
        if not who or not did or not evidence:
            report(line, "customer evidence row needs who, what they did, and evidence")
        if kind not in EVIDENCE_KINDS:
            report(line, f"kind '{kind}' is not one of: {', '.join(EVIDENCE_KINDS)}")
        if criterion != "-" and criterion not in numbers:
            report(line, f"criterion '{criterion}' is not a kill criterion number or '-'")

    if status.startswith("Decided"):
        if "open" in results:
            report(status_line, "a decided bet cannot have an open kill criterion")
        memo = "".join(t for _, t in bet.sections["Decision memo"]).strip()
        if not memo or memo.startswith("Not written"):
            report(status_line, "a decided bet needs a decision memo")
    return problems


def check_links(lines: list[tuple[int, str]], base: Path, path: str) -> list[str]:
    problems = []
    for number, text in lines:
        for target in LINK.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue
            if not (base / target.split("#")[0]).exists():
                problems.append(f"{path}:{number}: link target '{target}' does not exist")
    return problems


def check_file(path: Path, today: dt.date) -> list[str]:
    lines = strip_fences(path.read_text(encoding="utf-8").splitlines())
    bets = parse(lines)
    problems = [] if bets else [f"{path}:1: no '## BET-NNN: <name>' section found"]
    seen: set[str] = set()
    for bet in bets:
        if bet.bet_id in seen:
            problems.append(f"{path}:{bet.line}: {bet.bet_id}: duplicate bet id")
        seen.add(bet.bet_id)
        problems += check_bet(bet, today, str(path))
    return problems + check_links(lines, path.parent, str(path))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    problems = check_file(args.record, args.today)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"{args.record}: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
