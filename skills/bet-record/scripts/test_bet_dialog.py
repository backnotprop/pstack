import datetime as dt
import tempfile
import unittest
from pathlib import Path

from bet_dialog import MAX_QUESTIONS, dialog

TODAY = dt.date(2026, 11, 16)


def record(criteria_count: int) -> str:
    rows = "\n".join(
        f"| {n} | Name {n} | {n} users | rows | open |" for n in range(1, criteria_count + 1)
    )
    return f"""## BET-001: Monitor

**Core question.** Is it accurate?

**Status.** Framing

**Criteria confirmed.** Open

**Decision date.** Open

### Kill criteria

| # | Criterion | Threshold | Evidence that counts | Result |
| --- | --- | --- | --- | --- |
{rows}
""".replace("| 2 users |", "| 2 users, per [PRODUCT.md](PRODUCT.md) |")


class DialogTest(unittest.TestCase):
    def run_dialog(self, text: str, step: str, bet_id: str = "BET-001") -> list[dict]:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bets.md"
            path.write_text(text, encoding="utf-8")
            return dialog(path, bet_id, step, TODAY)

    def test_frame_asks_each_criterion_then_the_date(self):
        calls = self.run_dialog(record(5), "frame")
        questions = [q for call in calls for q in call["questions"]]
        self.assertEqual(
            [q["header"] for q in questions], [f"Criterion {n}" for n in range(1, 6)] + ["Decision"]
        )
        self.assertIn("'3 users'", questions[2]["question"])
        self.assertIn("'2 users, per PRODUCT.md'", questions[1]["question"])
        self.assertEqual(
            [o["label"] for o in questions[-1]["options"]],
            ["2026-11-30", "2026-12-07", "2026-12-14"],
        )

    def test_every_call_fits_the_question_tool(self):
        for count in (1, 3, 4, 6, 9):
            for call in self.run_dialog(record(count), "frame"):
                self.assertLessEqual(len(call["questions"]), MAX_QUESTIONS)
                for question in call["questions"]:
                    self.assertLessEqual(len(question["header"]), 12)
                    self.assertTrue(2 <= len(question["options"]) <= 4)

    def test_memo_offers_the_three_decisions_with_results(self):
        (call,) = self.run_dialog(record(2), "memo")
        (question,) = call["questions"]
        self.assertIn("1 open, 2 open", question["question"])
        self.assertEqual([o["label"] for o in question["options"]], ["Go", "No-go", "Pivot"])

    def test_frame_stops_when_criteria_are_confirmed(self):
        text = record(2).replace(
            "**Criteria confirmed.** Open", "**Criteria confirmed.** 2026-11-16"
        )
        with self.assertRaises(SystemExit):
            self.run_dialog(text, "frame")

    def test_unknown_bet_stops(self):
        with self.assertRaises(SystemExit):
            self.run_dialog(record(1), "frame", bet_id="BET-009")


if __name__ == "__main__":
    unittest.main()
