"""四步流水线：读页面、抽条款、执行、对照种草。"""

from __future__ import annotations

from rulecard.baseline import baseline_ticket
from rulecard.execute import run_rule
from rulecard.extract import extract_rule


def compile_and_run(venue: dict, age: int, height_m: float, benefits: list[str] | None = None) -> dict:
    rule = extract_rule(venue.get("page_text") or "", venue.get("promo_text") or "")
    compiled = run_rule(rule, age, height_m, benefits or [])
    naive = baseline_ticket(venue.get("promo_text") or "", venue.get("page_text") or "")
    gold = (venue.get("gold") or {}).get("ticket")
    return {
        "venue_id": venue["id"],
        "name": venue["name"],
        "verified": bool(venue.get("verified")),
        "source": venue.get("source") or "",
        "rule": rule,
        "compiled": compiled,
        "baseline_ticket": naive,
        "gold_ticket": gold,
        "compiled_correct": gold is None or compiled["ticket"] == gold,
        "baseline_correct": gold is None or naive == gold,
    }
