import tempfile
import unittest
from pathlib import Path

from check_diligence import check

TEMPLATE = (Path(__file__).parent.parent / "references" / "diligence-memo-template.md").read_text(
    encoding="utf-8"
)

GOOD = """# Diligence: h11

**Date.** 2026-11-16

**Question.** Can BET-001 use h11 for its HTTP checks?

**Recommendation.** Support with conditions

Pin the version.

1. Pin h11 in the lock file (C2).

## Code

| # | Finding | Evidence | Severity |
| --- | --- | --- | --- |
| C1 | Tests pass | out/pytest.txt | info |
| C2 | No pin in the README | README.md:12 | medium |

## Team

| # | Finding | Evidence | Severity |
| --- | --- | --- | --- |
| T1 | Two maintainers | git shortlog, out/authors.txt | low |

## Market

| # | Finding | Evidence | Severity |
| --- | --- | --- | --- |
| M1 | httpx wraps it | https://example.org, 2026-11-16 | info |

## Risks

The pin can lag security fixes (C2).

## Not checked

License of the test fixtures: not in scope.
"""


class CheckDiligenceTest(unittest.TestCase):
    def problems(self, text: str) -> list[str]:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memo.md"
            path.write_text(text, encoding="utf-8")
            return check(path)

    def test_a_complete_memo_passes(self):
        self.assertEqual(self.problems(GOOD), [])

    def test_the_template_fails_until_filled(self):
        self.assertTrue(any("placeholder" in p for p in self.problems(TEMPLATE)))

    def test_a_finding_needs_evidence(self):
        text = GOOD.replace("| out/pytest.txt |", "|  |")
        self.assertTrue(any("no evidence" in p for p in self.problems(text)))

    def test_a_high_finding_rules_out_plain_support(self):
        text = GOOD.replace("Support with conditions", "Support").replace("| medium |", "| high |")
        self.assertTrue(any("rules out" in p for p in self.problems(text)))

    def test_finding_numbers_match_their_area(self):
        text = GOOD.replace("| T1 |", "| C9 |")
        self.assertTrue(any("must be T" in p for p in self.problems(text)))

    def test_an_unknown_severity_fails(self):
        text = GOOD.replace("| low |", "| minor |")
        self.assertTrue(any("severity 'minor'" in p for p in self.problems(text)))

    def test_an_empty_area_must_move_to_not_checked(self):
        row = "| M1 | httpx wraps it | https://example.org, 2026-11-16 | info |\n"
        text = GOOD.replace(row, "")
        self.assertTrue(any("has no finding" in p for p in self.problems(text)))

    def test_an_empty_risks_section_fails(self):
        text = GOOD.replace("The pin can lag security fixes (C2).\n", "")
        self.assertTrue(any("'## Risks' is empty" in p for p in self.problems(text)))

    def test_conditions_are_required_and_name_findings(self):
        found = self.problems(GOOD.replace("1. Pin h11 in the lock file (C2).\n", ""))
        self.assertTrue(any("needs a numbered list" in p for p in found), found)
        found = self.problems(GOOD.replace("(C2).", "soon."))
        self.assertTrue(any("must name the finding" in p for p in found), found)

    def test_a_medium_finding_must_be_answered(self):
        text = GOOD.replace("(C2).", "(C1).").replace("security fixes (C2)", "security fixes")
        found = self.problems(text)
        self.assertTrue(any("finding C2 is high or medium" in p for p in found), found)

    def test_an_escaped_pipe_stays_in_one_cell(self):
        text = GOOD.replace("| out/pytest.txt |", "| uv run pytest -q \\| tail -1 |")
        self.assertEqual(self.problems(text), [])


if __name__ == "__main__":
    unittest.main()
