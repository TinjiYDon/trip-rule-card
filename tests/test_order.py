import unittest

from rulecard.extract import extract_rule
from rulecard.intent import parse_intent
from rulecard.load import get_venue
from rulecard.order import build_order_card


class OrderTests(unittest.TestCase):
    def test_order_card_family_tech_museum(self):
        venue = get_venue("tech-museum")
        card = build_order_card(
            venue,
            [
                {"id": "a", "name": "成人1", "age": 35, "height_m": 1.7},
                {"id": "c", "name": "儿童1", "age": 10, "height_m": 1.4},
            ],
        )
        self.assertEqual(card["summary"]["n"], 2)
        self.assertEqual(card["per_person"][1]["ticket"], "half")
        self.assertTrue(card["promo_conflict_any"])

    def test_quota_and_escort_extracted(self):
        venue = get_venue("tech-museum")
        rule = extract_rule(venue["page_text"], "")
        self.assertEqual(rule["free_children_per_adult"], 3)
        self.assertIsNone(rule["escort_required_under_age"])

        museum = get_venue("chnmuseum")
        escort_rule = extract_rule(museum["page_text"], "")
        self.assertEqual(escort_rule["escort_required_under_age"], 14)

    def test_escort_blocker_without_adult(self):
        venue = get_venue("chnmuseum")
        card = build_order_card(venue, [{"id": "c", "name": "儿童1", "age": 7, "height_m": 1.3}])
        codes = [b["code"] for b in card["blockers"]]
        self.assertIn("escort_required", codes)
        self.assertFalse(card["can_book"])

    def test_intent_science_museum(self):
        intent = parse_intent("带孩子去科技馆能不能免票")
        self.assertEqual(intent["venue_id"], "tech-museum")
        self.assertGreaterEqual(len(intent["travelers"]), 2)


if __name__ == "__main__":
    unittest.main()
