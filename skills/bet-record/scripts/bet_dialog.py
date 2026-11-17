#!/usr/bin/env python3
"""Print the AskUserQuestion calls for one operator step of one bet, as JSON."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections.abc import Callable
from pathlib import Path

from check_bet import CRITERIA_HEADER, Bet, parse, strip_fences, table

MAX_QUESTIONS = 4
DECISION_WEEKS = (2, 3, 4)

Question = dict[str, object]
LINK_TEXT = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def criteria(bet: Bet) -> list[list[str]]:
    header, rows = table(bet.sections.get("Kill criteria", []))
    if header != CRITERIA_HEADER:
        raise SystemExit(f"{bet.bet_id}: kill criteria table is malformed; run check_bet.py first")
    return [[LINK_TEXT.sub(r"\1", cell) for cell in cells] for _, cells in rows]


def frame_questions(bet: Bet, today: dt.date) -> list[Question]:
    confirmed = bet.fields.get("Criteria confirmed", ("Open", 0))[0]
    if not confirmed.startswith("Open"):
        raise SystemExit(
            f"{bet.bet_id}: criteria were confirmed on {confirmed}; "
            "only the operator can reopen them"
        )
    questions = [
        {
            "question": (
                f"{bet.bet_id} criterion {number}, {name}: "
                f"keep the threshold '{threshold}', measured by {evidence}?"
            ),
            "header": f"Criterion {number}",
            "multiSelect": False,
            "options": [
                {"label": "Confirm", "description": f"Keep '{threshold}' as the kill threshold."},
                {"label": "Drop", "description": "Remove this criterion from the bet."},
            ],
        }
        for number, name, threshold, evidence, _ in criteria(bet)
    ]
    questions.append(
        {
            "question": f"{bet.bet_id}: on which date do you decide go, no-go, or pivot?",
            "header": "Decision",
            "multiSelect": False,
            "options": [
                {
                    "label": (today + dt.timedelta(weeks=weeks)).isoformat(),
                    "description": f"{weeks} weeks from {today.isoformat()}.",
                }
                for weeks in DECISION_WEEKS
            ],
        }
    )
    return questions


def memo_questions(bet: Bet, today: dt.date) -> list[Question]:
    results = ", ".join(f"{number} {result}" for number, _, _, _, result in criteria(bet))
    return [
        {
            "question": (
                f"{bet.bet_id} criteria results are: {results}. Which decision do you take?"
            ),
            "header": "Decision",
            "multiSelect": False,
            "options": [
                {"label": "Go", "description": "Continue the bet toward production."},
                {
                    "label": "No-go",
                    "description": "Stop the bet. The memo records what was learned.",
                },
                {
                    "label": "Pivot",
                    "description": "Stop this bet and frame a new bet from the new evidence.",
                },
            ],
        }
    ]


STEPS: dict[str, Callable[[Bet, dt.date], list[Question]]] = {
    "frame": frame_questions,
    "memo": memo_questions,
}


def dialog(record: Path, bet_id: str, step: str, today: dt.date) -> list[dict[str, list[Question]]]:
    bets = {
        bet.bet_id: bet
        for bet in parse(strip_fences(record.read_text(encoding="utf-8").splitlines()))
    }
    if bet_id not in bets:
        raise SystemExit(f"{record}: no section for {bet_id}")
    questions = STEPS[step](bets[bet_id], today)
    return [
        {"questions": questions[i : i + MAX_QUESTIONS]}
        for i in range(0, len(questions), MAX_QUESTIONS)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("bet_id")
    parser.add_argument("step", choices=sorted(STEPS))
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    print(json.dumps(dialog(args.record, args.bet_id, args.step, args.today), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
