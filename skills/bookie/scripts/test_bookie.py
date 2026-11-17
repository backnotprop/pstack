import datetime as dt
import tempfile
import unittest
from pathlib import Path

from bookie import (
    HANDOFF,
    PRELAUNCH,
    STAGES,
    find_bet,
    finish,
    next_stage,
    save_progress,
    status,
)

TODAY = dt.date(2026, 11, 17)

RECORD = """## BET-001: Monitor

**Core question.** Is it accurate?

**Status.** {status}

**Criteria confirmed.** {confirmed}

**Decision date.** {decision}

### Kill criteria

| # | Criterion | Threshold | Evidence that counts | Result |
| --- | --- | --- | --- | --- |
| 1 | Pull | 3 users | logs | {result} |

### Build-or-buy scan

{scan}

### Build log

| Date | Unit | Evidence |
| --- | --- | --- |
{log}

### Customer evidence

| Date | Who | Kind | What they did | Evidence | Criterion |
| --- | --- | --- | --- | --- | --- |
{evidence}

### Decision memo

Not written.
"""

FRAMED = {
    "status": "Building",
    "confirmed": "2026-11-16",
    "decision": "2026-12-14",
    "result": "open",
    "scan": "Pingdom costs money; build.",
    "log": "",
    "evidence": "",
}


class BookieTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.record = Path(self.folder.name) / "bets.md"

    def tearDown(self):
        self.folder.cleanup()

    def write(self, **values):
        self.record.write_text(RECORD.format(**{**FRAMED, **values}), encoding="utf-8")

    def advance(self, *names, **kwargs):
        for name in names:
            finish(self.record, "BET-001", name, TODAY, **kwargs)

    def test_a_missing_bet_starts_at_frame_with_a_failed_gate(self):
        result = next_stage(self.record, "BET-001", TODAY)
        self.assertEqual(result["stage"], "frame")
        self.assertIn("no section", result["gate"])
        self.assertEqual(result["calls"], [])

    def test_frame_with_open_criteria_asks_the_bet_record_questions(self):
        self.write(status="Framing", confirmed="Open", decision="Open")
        result = next_stage(self.record, "BET-001", TODAY)
        headers = [q["header"] for call in result["calls"] for q in call["questions"]]
        self.assertEqual(headers, ["Criterion 1", "Decision"])
        with self.assertRaisesRegex(SystemExit, "frame gate"):
            self.advance("frame")

    def test_confirmed_frame_passes_and_moves_to_build_or_buy(self):
        self.write()
        self.advance("frame")
        self.assertEqual(next_stage(self.record, "BET-001", TODAY)["stage"], "build-or-buy")

    def test_a_stage_cannot_finish_out_of_order(self):
        self.write()
        with self.assertRaisesRegex(SystemExit, "not the current stage"):
            self.advance("scope")

    def test_frame_score_and_memo_cannot_be_skipped(self):
        self.write()
        with self.assertRaisesRegex(SystemExit, "cannot be skipped"):
            finish(self.record, "BET-001", "frame", TODAY, note="no time", skip=True)

    def test_a_skip_needs_a_reason_and_is_recorded(self):
        self.write()
        self.advance("frame")
        with self.assertRaisesRegex(SystemExit, "reason"):
            finish(self.record, "BET-001", "build-or-buy", TODAY, skip=True)
        finish(
            self.record,
            "BET-001",
            "build-or-buy",
            TODAY,
            note="internal tool",
            skip=True,
        )
        self.assertEqual(status(self.record, "BET-001")[1]["status"], "skipped")

    def test_an_empty_scan_fails_its_gate(self):
        self.write(scan="<Existing products>")
        self.advance("frame")
        with self.assertRaisesRegex(SystemExit, "Build-or-buy scan"):
            self.advance("build-or-buy")

    def test_evidence_must_exist_beside_the_record(self):
        self.write()
        self.advance("frame", "build-or-buy")
        with self.assertRaisesRegex(SystemExit, "does not exist"):
            self.advance("scope", evidence="examples/")
        (Path(self.folder.name) / "examples").mkdir()
        self.advance("scope", evidence="examples/")
        self.assertEqual(next_stage(self.record, "BET-001", TODAY)["stage"], "evals")

    def test_harden_needs_every_item_and_keeps_partial_answers(self):
        self.write(log="| 2026-11-17 | slice | abc1234 |")
        (Path(self.folder.name) / "e").mkdir()
        self.advance("frame", "build-or-buy")
        self.advance("scope", "evals", evidence="e")
        self.advance("build")
        with self.assertRaisesRegex(SystemExit, "Rollback"):
            self.advance("harden", answers={"Tracing": "done"})
        rest = {label: "done" for label, _ in PRELAUNCH if label != "Tracing"}
        self.advance("harden", answers=rest)
        self.assertEqual(next_stage(self.record, "BET-001", TODAY)["stage"], "users")

    def test_iterate_waits_for_the_decision_date_unless_given_a_reason(self):
        self.write(
            log="| 2026-11-17 | slice | abc |",
            evidence="| 2026-11-17 | owner A | usage | Added 4 sites | rows.txt | 1 |",
        )
        progress = {s.name: {"status": "done"} for s in STAGES[:7]}
        save_progress(self.record, "BET-001", progress)
        with self.assertRaisesRegex(SystemExit, "in the future"):
            self.advance("iterate")
        self.advance("iterate", note="every criterion has its evidence")
        self.assertEqual(next_stage(self.record, "BET-001", TODAY)["stage"], "score")

    def test_score_needs_binary_results_and_memo_needs_a_decision(self):
        self.write()
        save_progress(self.record, "BET-001", {s.name: {"status": "done"} for s in STAGES[:8]})
        with self.assertRaisesRegex(SystemExit, "still open: 1"):
            self.advance("score")
        self.write(result="met")
        self.advance("score")
        with self.assertRaisesRegex(SystemExit, "not Decided"):
            self.advance("memo")
        self.write(result="met", status="Decided: go")
        self.advance("memo")
        self.assertIsNone(next_stage(self.record, "BET-001", TODAY)["stage"])

    def test_every_question_fits_the_question_tool(self):
        self.write(status="Framing", confirmed="Open", decision="Open")
        bet = find_bet(self.record, "BET-001")
        assert bet is not None
        asked = []
        for stage in STAGES:
            for question in stage.questions(bet, TODAY):
                asked.append(question["header"])
                self.assertLessEqual(len(question["header"]), 12, question["header"])
                self.assertTrue(2 <= len(question["options"]) <= 4, question["question"])
                for option in question["options"]:
                    self.assertLessEqual(len(option["label"].split()), 5, option["label"])
        self.assertEqual(asked.count("Pre-launch"), len(PRELAUNCH) // 4)
        self.assertEqual(asked.count("Handoff"), len(HANDOFF) // 4)


if __name__ == "__main__":
    unittest.main()
