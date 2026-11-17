#!/usr/bin/env python3
"""Check a diligence memo. Prints one line per problem and exits 1 if any."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RECOMMENDATIONS = ("Support", "Support with conditions", "Do not support")
SEVERITIES = ("high", "medium", "low", "info")
FIELDS = ("Date", "Question", "Recommendation")
AREAS = {"Code": "C", "Team": "T", "Market": "M"}
PROSE_SECTIONS = ("Risks", "Not checked")
FINDINGS_HEADER = ["#", "Finding", "Evidence", "Severity"]

TITLE = re.compile(r"^# Diligence: \S")
FIELD_LINE = re.compile(r"^\*\*([^*]+)\.\*\* ?(.*)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PLACEHOLDER = re.compile(r"<[^>]+>")
FINDING_ID = re.compile(r"\b[CTM]\d+\b")
CONDITION = re.compile(r"^\d+\. ")
CELL_SPLIT = re.compile(r"(?<!\\)\|")

Lines = list[tuple[int, str]]


def sections(lines: list[str]) -> tuple[dict[str, tuple[str, int]], dict[str, Lines]]:
    """Return the fields, and the body of each section. Key "" holds the text after the fields."""
    fields: dict[str, tuple[str, int]] = {}
    body: dict[str, Lines] = {"": []}
    current: str | None = None
    for number, text in enumerate(lines, start=1):
        if text.startswith("## "):
            current = text[3:].strip()
            body[current] = []
        elif current is None:
            match = FIELD_LINE.match(text)
            if match:
                fields[match.group(1)] = (match.group(2).strip(), number)
            else:
                body[""].append((number, text))
        else:
            body[current].append((number, text))
    return fields, body


def table_rows(rows: Lines) -> tuple[list[str] | None, list[tuple[int, list[str]]]]:
    cells = [
        (n, [c.strip() for c in CELL_SPLIT.split(t.strip().strip("|"))])
        for n, t in rows
        if t.strip().startswith("|")
    ]
    if not cells:
        return None, []
    body = [c for c in cells[1:] if not all(set(x) <= set("-: ") for x in c[1])]
    return cells[0][1], body


def check(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    problems: list[str] = []

    def report(line: int, message: str) -> None:
        problems.append(f"{path}:{line}: {message}")

    if not lines or not TITLE.match(lines[0]):
        report(1, "the first line must be '# Diligence: <subject>'")
    for number, text in enumerate(lines, start=1):
        if PLACEHOLDER.search(text):
            report(number, "the memo still has a <placeholder>")

    fields, body = sections(lines)
    for name in FIELDS:
        if name not in fields:
            report(1, f"missing field '**{name}.**'")
    for name in (*AREAS, *PROSE_SECTIONS):
        if name not in body:
            report(1, f"missing section '## {name}'")
    if problems:
        return problems

    date, date_line = fields["Date"]
    if not DATE.match(date):
        report(date_line, f"date must be YYYY-MM-DD, not '{date}'")
    recommendation, recommendation_line = fields["Recommendation"]
    if recommendation not in RECOMMENDATIONS:
        report(recommendation_line, f"recommendation must be one of: {', '.join(RECOMMENDATIONS)}")

    severities: list[str] = []
    serious: list[tuple[int, str]] = []
    for area, prefix in AREAS.items():
        header, rows = table_rows(body[area])
        if header != FINDINGS_HEADER:
            report(1, f"'## {area}' needs the table header: | {' | '.join(FINDINGS_HEADER)} |")
            continue
        if not rows:
            report(1, f"'## {area}' has no finding; give the reason under '## Not checked'")
        for line, cells in rows:
            if len(cells) != len(FINDINGS_HEADER):
                report(line, "finding row has the wrong number of cells")
                continue
            number, finding, evidence, severity = cells
            if not re.fullmatch(rf"{prefix}\d+", number):
                report(line, f"finding number '{number}' must be {prefix} and a number")
            if not finding:
                report(line, "finding has no text")
            if not evidence:
                report(line, "finding has no evidence; move it to '## Not checked'")
            if severity not in SEVERITIES:
                report(line, f"severity '{severity}' is not one of: {', '.join(SEVERITIES)}")
            severities.append(severity)
            if severity in ("high", "medium"):
                serious.append((line, number))

    for name in PROSE_SECTIONS:
        if not "".join(text for _, text in body[name]).strip():
            report(1, f"'## {name}' is empty")
    conditions = [(n, t) for n, t in body[""] if CONDITION.match(t)]
    if recommendation == "Support with conditions" and not conditions:
        report(recommendation_line, "'Support with conditions' needs a numbered list of conditions")
    for line, text in conditions:
        if not FINDING_ID.search(text):
            report(line, "each condition must name the finding numbers it answers")
    answered = "".join(t for _, t in body[""] + body["Risks"])
    for line, number in serious:
        if not re.search(rf"\b{number}\b", answered):
            report(
                line, f"finding {number} is high or medium; name it in a condition or under Risks"
            )
    if recommendation == "Support" and "high" in severities:
        report(recommendation_line, "a high finding rules out a plain 'Support'")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("memo", type=Path)
    args = parser.parse_args(argv)
    problems = check(args.memo)
    for problem in problems:
        print(problem)
    if not problems:
        print(f"{args.memo}: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
