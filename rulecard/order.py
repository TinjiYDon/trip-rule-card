"""订单会话层：编译一次，执行多人，汇总成 OrderCard。"""

from __future__ import annotations

from rulecard.coverage import rule_coverage
from rulecard.direct import drop_and_ticket, first_number_ticket, keyword_ticket
from rulecard.execute import TICKET_LABEL, run_rule
from rulecard.extract import extract_rule
from rulecard.repair import repair_rule
from rulecard.schema_check import validate_rule
from rulecard.segment import segment


def build_order_card(
    venue: dict,
    travelers: list[dict],
    visit_date: str | None = None,
) -> dict:
    """travelers: [{id, name?, age, height_m, tags?}] tags 可含 student。"""
    page = venue.get("page_text") or ""
    promo = venue.get("promo_text") or ""
    clauses = segment(page)
    proposed = extract_rule(page, promo)
    issues = validate_rule(proposed)
    rule, repairs = repair_rule(proposed, page)
    coverage = rule_coverage(page, rule)

    per_person = []
    for person in travelers:
        age = int(person.get("age", 7))
        height = float(person.get("height_m", 1.3))
        tags = person.get("tags") or []
        benefits = ["child", "student"] if "student" in tags or person.get("student") else []
        compiled = run_rule(rule, age, height, benefits)
        keyword, _ = keyword_ticket(promo, page)
        first, _ = first_number_ticket(page, age, height)
        ablation, _ = drop_and_ticket(page, promo, age, height)
        per_person.append(
            {
                "id": person.get("id") or person.get("name") or f"p{len(per_person)+1}",
                "name": person.get("name") or person.get("id") or "出行人",
                "age": age,
                "height_m": height,
                "ticket": compiled["ticket"],
                "ticket_label": compiled["ticket_label"],
                "clause": compiled["ticket_clause"],
                "promo_conflict": bool(compiled["promo"]["conflict"]),
                "benefits_ok": bool(compiled["benefits"]["ok"]),
                "benefit_notes": compiled["benefits"]["notes"],
                "baseline_ticket": keyword,
                "first_number_ticket": first,
                "ablation_ticket": ablation,
                "compiled": compiled,
            }
        )

    summary = {
        "free": sum(1 for row in per_person if row["ticket"] == "free"),
        "half": sum(1 for row in per_person if row["ticket"] == "half"),
        "full": sum(1 for row in per_person if row["ticket"] == "full"),
        "n": len(per_person),
    }
    blockers = _blockers(rule, per_person, coverage, issues)
    warnings = []
    if coverage["ratio"] < 0.999 and coverage["uncovered"]:
        warnings.append(
            {
                "code": "low_coverage",
                "message": f"有 {len(coverage['uncovered'])} 句票务相关文字未进入规则，结论可能不完整",
                "samples": coverage["uncovered"][:3],
            }
        )
    if visit_date:
        warnings.append(
            {
                "code": "calendar_hook",
                "message": f"已记录出行日 {visit_date}；当前语料未挂节日特则，按常规则执行",
            }
        )

    release = per_person[0]["compiled"]["release"] if per_person else "页面未写放票时刻"
    can_book = not any(b["code"] in ("escort_required", "quota_exceeded", "schema_issue") for b in blockers)

    return {
        "venue_id": venue.get("id"),
        "name": venue.get("name"),
        "verified": bool(venue.get("verified")),
        "visit_date": visit_date,
        "rule": rule,
        "schema_issues": issues,
        "repairs": repairs,
        "coverage": coverage,
        "segments": clauses,
        "per_person": per_person,
        "summary": summary,
        "summary_text": _summary_text(summary),
        "blockers": blockers,
        "warnings": warnings,
        "release": release,
        "can_book": can_book,
        "promo_conflict_any": any(row["promo_conflict"] for row in per_person),
        "ticket_labels": TICKET_LABEL,
    }


def _summary_text(summary: dict) -> str:
    parts = []
    if summary["free"]:
        parts.append(f"{summary['free']} 人免票")
    if summary["half"]:
        parts.append(f"{summary['half']} 人半票")
    if summary["full"]:
        parts.append(f"{summary['full']} 人全票")
    return "，".join(parts) if parts else "未算出票种"


def _blockers(rule: dict, per_person: list[dict], coverage: dict, issues: list[str]) -> list[dict]:
    blockers: list[dict] = []
    if issues:
        blockers.append({"code": "schema_issue", "message": "规则结构未通过校验：" + "、".join(issues)})

    escort_age = rule.get("escort_required_under_age")
    if escort_age is not None:
        adults = [p for p in per_person if p["age"] >= int(escort_age)]
        minors = [p for p in per_person if p["age"] < int(escort_age)]
        if minors and not adults:
            blockers.append(
                {
                    "code": "escort_required",
                    "message": f"未满 {escort_age} 周岁须由成年人代约/陪同，当前出行人里没有成人",
                }
            )

    quota = rule.get("free_children_per_adult")
    if quota is not None:
        adults = [p for p in per_person if p["age"] >= 18]
        free_kids = [p for p in per_person if p["ticket"] == "free" and p["age"] < 18]
        capacity = max(len(adults), 0) * int(quota)
        # 无成人时，免票童仍可能被 escort 拦；这里单独报超额
        if adults and len(free_kids) > capacity:
            blockers.append(
                {
                    "code": "quota_exceeded",
                    "message": f"免票儿童 {len(free_kids)} 人，超过每成人可带 {quota} 人的限额（当前成人 {len(adults)}）",
                }
            )

    if any(p["promo_conflict"] for p in per_person):
        blockers.append(
            {
                "code": "promo_conflict",
                "message": "种草宣称免票，但至少一位出行人按条款不是免票",
            }
        )
    return blockers
