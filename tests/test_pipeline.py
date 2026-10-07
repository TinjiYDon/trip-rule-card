import unittest

from rulecard.execute import judge_ticket, run_rule
from rulecard.load import list_venues
from rulecard.pipeline import compile_and_run


class ExecuteTests(unittest.TestCase):
    def test_height_half(self):
        rule = {"mode": "height", "free_height_m": 1.2, "half_height_m": 1.4, "clause_ticket": "1.4米半票"}
        ticket, _ = judge_ticket(rule, 7, 1.3)
        self.assertEqual(ticket, "half")

    def test_both_fails_when_too_tall(self):
        rule = {
            "mode": "both",
            "half_height_m": 1.4,
            "half_age_lt": 14,
            "clause_ticket": "同时满足",
        }
        ticket, _ = judge_ticket(rule, 7, 1.45)
        self.assertEqual(ticket, "full")

    def test_benefits_exclude(self):
        rule = {
            "mode": "age",
            "free_age_lt": 18,
            "benefits": [
                {"id": "child", "label": "儿童免费", "excludes": ["student"]},
                {"id": "student", "label": "学生票", "excludes": ["child"]},
            ],
            "clause_benefit": "不能叠加",
        }
        result = run_rule(rule, 7, 1.3, ["child", "student"])
        self.assertFalse(result["benefits"]["ok"])


class PipelineTests(unittest.TestCase):
    def test_compiled_beats_or_ties_baseline_on_every_seed(self):
        venues = list_venues()
        self.assertGreaterEqual(len(venues), 8)
        for venue in venues:
            gold = venue["gold"]
            result = compile_and_run(venue, gold["age"], gold["height_m"])
            self.assertTrue(
                result["compiled_correct"],
                f"{venue['id']} compiled={result['compiled']['ticket']} gold={gold['ticket']} rule={result['rule']}",
            )


if __name__ == "__main__":
    unittest.main()
