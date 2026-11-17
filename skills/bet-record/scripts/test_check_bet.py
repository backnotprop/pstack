import datetime as dt
import tempfile
import unittest
from pathlib import Path

from check_bet import check_file

TEMPLATE = (Path(__file__).parent.parent / "references" / "bet-record-template.md").read_text(
    encoding="utf-8"
)
TODAY = dt.date(2026, 11, 20)

BUILDING = """## BET-001: Monitor

**Core question.** Is it accurate?

**Status.** Building. Slice 1.

**Criteria confirmed.** 2026-11-16

**Decision date.** 2026-12-14

### Kill criteria

| # | Criterion | Threshold | Evidence that counts | Result |
| --- | --- | --- | --- | --- |
| 1 | Feasibility | 0 false alerts | check_results rows | open |

### Build-or-buy scan

Open.

### Build log

| Date | Unit | Evidence |
| --- | --- | --- |
| 2026-11-16 | Slice 1 design | commit abc1234 |

### Customer evidence

None.

### Decision memo

Not written.
"""


def problems(text: str, today: dt.date = TODAY, extra: dict[str, str] | None = None) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        record = Path(tmp) / "bets.md"
        record.write_text(text, encoding="utf-8")
        for name, body in (extra or {}).items():
            (Path(tmp) / name).write_text(body, encoding="utf-8")
        return check_file(record, today)


class CheckBet(unittest.TestCase):
    def test_template_copied_as_a_new_bet_passes(self):
        self.assertEqual(problems(TEMPLATE.replace("BET-NNN: <name>", "BET-002: New idea")), [])

    def test_valid_building_bet_passes(self):
        self.assertEqual(problems(BUILDING), [])

    def test_building_without_confirmed_criteria_or_date_fails(self):
        text = BUILDING.replace(
            "**Criteria confirmed.** 2026-11-16", "**Criteria confirmed.** Open"
        ).replace("**Decision date.** 2026-12-14", "**Decision date.** Open. The owner sets it.")
        found = problems(text)
        self.assertTrue(any("'Criteria confirmed' must be a date" in p for p in found), found)
        self.assertTrue(any("'Decision date' must be a date" in p for p in found), found)

    def test_unknown_status_fails(self):
        self.assertTrue(
            any(
                "is not one of" in p
                for p in problems(BUILDING.replace("Building. Slice 1.", "Coding"))
            )
        )

    def test_unknown_result_fails(self):
        self.assertTrue(
            any(
                "result 'almost'" in p for p in problems(BUILDING.replace("| open |", "| almost |"))
            )
        )

    def test_missing_threshold_fails(self):
        self.assertTrue(
            any("no threshold" in p for p in problems(BUILDING.replace("0 false alerts", "")))
        )

    def test_placeholder_after_framing_fails(self):
        found = problems(BUILDING.replace("0 false alerts", "<a number>"))
        self.assertTrue(any("placeholder" in p for p in found), found)

    def test_passed_decision_date_without_decision_fails(self):
        found = problems(BUILDING, today=dt.date(2026, 12, 20))
        self.assertTrue(any("has passed" in p for p in found), found)

    def test_decided_bet_needs_decided_criteria_and_memo(self):
        found = problems(BUILDING.replace("Building. Slice 1.", "Decided: go"))
        self.assertTrue(any("open kill criterion" in p for p in found), found)
        self.assertTrue(any("needs a decision memo" in p for p in found), found)

    def test_decided_bet_with_results_and_memo_passes(self):
        text = BUILDING.replace("Building. Slice 1.", "Decided: no-go").replace(
            "| open |", "| not met |"
        )
        text = text.replace(
            "Not written.", "1. Recommendation: no-go, because criterion 1 was not met."
        )
        self.assertEqual(problems(text), [])

    def test_build_log_row_without_date_fails(self):
        found = problems(
            BUILDING.replace("| 2026-11-16 | Slice 1 design |", "| soon | Slice 1 design |")
        )
        self.assertTrue(any("YYYY-MM-DD date" in p for p in found), found)

    def test_broken_relative_link_fails_and_real_link_passes(self):
        self.assertTrue(
            any("does not exist" in p for p in problems(BUILDING + "\nSee [plan](PLAN.md).\n"))
        )
        self.assertEqual(
            problems(BUILDING + "\nSee [plan](PLAN.md).\n", extra={"PLAN.md": "x"}), []
        )

    def test_bets_inside_code_fences_are_ignored(self):
        self.assertEqual(problems(BUILDING + "\n```markdown\n## BET-009: Example\n```\n"), [])

    def test_duplicate_bet_id_fails(self):
        self.assertTrue(any("duplicate bet id" in p for p in problems(BUILDING + "\n" + BUILDING)))

    def test_customer_evidence_rows_pass_when_complete(self):
        table = (
            "| Date | Who | Kind | What they did | Evidence | Criterion |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 2026-11-20 | Agency owner A | usage | Added 4 sites | out/a.txt | 1 |\n"
            "| 2026-11-21 | Agency owner B | interview | Said they would pay | notes/b.md | - |\n"
        )
        self.assertEqual(problems(BUILDING.replace("None.\n", table)), [])

    def test_customer_evidence_row_rules(self):
        table = (
            "| Date | Who | Kind | What they did | Evidence | Criterion |\n"
            "| --- | --- | --- | --- | --- | --- |\n"
            "| 2026-11-20 | A | compliment | Liked it | notes/a.md | 1 |\n"
            "| 2026-11-21 | B | payment | Paid |  | 9 |\n"
        )
        found = problems(BUILDING.replace("None.\n", table))
        self.assertTrue(any("kind 'compliment'" in p for p in found), found)
        self.assertTrue(any("needs who, what they did, and evidence" in p for p in found), found)
        self.assertTrue(any("criterion '9'" in p for p in found), found)

    def test_a_bet_with_users_needs_customer_evidence(self):
        text = BUILDING.replace("**Status.** Building. Slice 1.", "**Status.** With users")
        self.assertTrue(any("needs a customer evidence table" in p for p in problems(text)))


if __name__ == "__main__":
    unittest.main()
