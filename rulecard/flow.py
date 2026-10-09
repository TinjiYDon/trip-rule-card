"""六步数据流：分句、抽槽、校验、修补、执行、对照朴素读法。"""

from __future__ import annotations

from rulecard.coverage import rule_coverage
from rulecard.direct import drop_and_ticket, first_number_ticket, keyword_ticket
from rulecard.errors import classify
from rulecard.execute import run_rule
from rulecard.extract import extract_rule
from rulecard.llm_propose import propose_with_llm
from rulecard.repair import repair_rule
from rulecard.schema_check import validate_rule
from rulecard.segment import segment


def compile_and_run(venue: dict, age: int, height_m: float, benefits: list[str] | None = None) -> dict:
    page = venue.get("page_text") or ""
    promo = venue.get("promo_text") or ""
    clauses = segment(page)
    proposed = extract_rule(page, promo)
    issues = validate_rule(proposed)
    rule, repairs = repair_rule(proposed, page)
    coverage = rule_coverage(page, rule)
    compiled = run_rule(rule, age, height_m, benefits or [])
    keyword, keyword_why = keyword_ticket(promo, page)
    first, first_why = first_number_ticket(page, age, height_m)
    ablation, ablation_why = drop_and_ticket(page, promo, age, height_m)
    llm_rule, llm_note = propose_with_llm(page, promo)
    gold = (venue.get("gold") or {}).get("ticket") if venue.get("gold") else None
    tags = classify(page, rule, compiled["ticket"], ablation, gold, issues)
    trace = [
        {"stage": "分句", "summary": f"{len(clauses)} 句", "detail": " / ".join(item["text"] for item in clauses[:4])},
        {"stage": "抽槽", "summary": f"判定方式 {rule.get('mode')}", "detail": rule.get("clause_ticket") or ""},
        {"stage": "校验", "summary": "通过" if not issues else "、".join(issues), "detail": ""},
        {"stage": "修补", "summary": "无" if not repairs else "；".join(repairs), "detail": ""},
        {"stage": "执行", "summary": compiled["ticket_label"], "detail": compiled["ticket_clause"]},
        {"stage": "对照", "summary": f"种草 {keyword} / 首数 {first} / 消融 {ablation}", "detail": llm_note},
    ]
    return {
        "venue_id": venue.get("id"),
        "name": venue.get("name"),
        "verified": bool(venue.get("verified")),
        "source": venue.get("source") or "",
        "rule": rule,
        "compiled": compiled,
        "baseline_ticket": keyword,
        "baseline_why": keyword_why,
        "first_number_ticket": first,
        "first_number_why": first_why,
        "ablation_ticket": ablation,
        "ablation_why": ablation_why,
        "llm_note": llm_note,
        "llm_used": llm_rule is not None,
        "gold_ticket": gold,
        "compiled_correct": None if gold is None else compiled["ticket"] == gold,
        "baseline_correct": None if gold is None else keyword == gold,
        "first_number_correct": None if gold is None else first == gold,
        "errors": tags,
        "schema_issues": issues,
        "repairs": repairs,
        "coverage": coverage,
        "segments": clauses,
        "trace": trace,
    }
