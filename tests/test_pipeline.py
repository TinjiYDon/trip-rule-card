import unittest

from rulecard.direct import drop_and_ticket, first_number_ticket
from rulecard.errors import classify
from rulecard.execute import judge_ticket, run_rule
from rulecard.extract import extract_rule
from rulecard.load import get_venue, list_venues
from rulecard.pipeline import compile_and_run
from rulecard.repair import repair_rule


class ExecuteTests(unittest.TestCase):
    def test_height_half(self):
        rule = {"mode": "height", "free_height_m": 1.2, "half_height_m": 1.4, "clause_ticket": "1.4米半票"}
        ticket, _ = judge_ticket(rule, 7, 1.3)
        self.assertEqual(ticket, "half")

    def test_inclusive_bound_counts_equal(self):
        rule = {"mode": "height", "free_height_m": 1.3, "free_height_inclusive": True, "clause_ticket": "含"}
        ticket, _ = judge_ticket(rule, 8, 1.3)
        self.assertEqual(ticket, "free")

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


class ExtractTests(unittest.TestCase):
    def test_cstm_half_when_over_free_line(self):
        venue = get_venue("tech-museum")
        rule = extract_rule(venue["page_text"], venue["promo_text"])
        self.assertEqual(rule["mode"], "either")
        self.assertTrue(rule["free_age_inclusive"])
        self.assertTrue(rule["free_height_inclusive"])
        ticket, _ = judge_ticket(rule, 10, 1.4)
        self.assertEqual(ticket, "half")
        edge, _ = judge_ticket(rule, 8, 1.5)
        self.assertEqual(edge, "free")

    def test_conjunction_without_the_phrase(self):
        venue = get_venue("and-plain")
        rule = extract_rule(venue["page_text"], "")
        self.assertEqual(rule["mode"], "both")

    def test_repair_swaps_inverted_heights(self):
        rule = {"mode": "height", "free_height_m": 1.5, "half_height_m": 1.2}
        fixed, notes = repair_rule(rule, "1.5米至1.2米")
        self.assertEqual(fixed["free_height_m"], 1.2)
        self.assertTrue(notes)


class PipelineTests(unittest.TestCase):
    def test_compiled_matches_gold_when_gold_exists(self):
        venues = list_venues()
        self.assertGreaterEqual(len(venues), 12)
        scored = 0
        for venue in venues:
            gold = venue.get("gold") or {}
            result = compile_and_run(venue, gold.get("age", 7), gold.get("height_m", 1.3))
            if result["compiled_correct"] is None:
                self.assertIn("no_threshold", result["errors"])
                continue
            scored += 1
            self.assertTrue(
                result["compiled_correct"],
                f"{venue['id']} compiled={result['compiled']['ticket']} gold={gold.get('ticket')} rule={result['rule']}",
            )
        self.assertGreaterEqual(scored, 12)

    def test_naive_readers_miss_tech_museum(self):
        venue = get_venue("tech-museum")
        result = compile_and_run(venue, 10, 1.4)
        self.assertEqual(result["compiled"]["ticket"], "half")
        self.assertEqual(result["baseline_ticket"], "free")
        self.assertEqual(result["first_number_ticket"], "full")
        self.assertNotEqual(first_number_ticket(venue["page_text"], 10, 1.4)[0], "half")

    def test_dropping_and_changes_both_gate(self):
        venue = get_venue("both-gate")
        result = compile_and_run(venue, 7, 1.45)
        self.assertEqual(result["compiled"]["ticket"], "full")
        self.assertEqual(result["ablation_ticket"], "half")
        self.assertIn("dual_threshold", result["errors"])
        self.assertEqual(drop_and_ticket(venue["page_text"], venue["promo_text"], 7, 1.45)[0], "half")

    def test_board_is_not_a_score(self):
        venue = get_venue("heldout-board")
        result = compile_and_run(venue, 7, 1.3)
        self.assertIsNone(result["compiled_correct"])
        tags = classify(venue["page_text"], result["rule"], result["compiled"]["ticket"], result["ablation_ticket"], None)
        self.assertIn("no_threshold", tags)


if __name__ == "__main__":
    unittest.main()
