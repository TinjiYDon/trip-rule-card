"""执行已编译规则。这一层不读散文，只吃结构化规则。"""

from __future__ import annotations

TICKET_LABEL = {"free": "免票", "half": "半票", "full": "全票"}
_RANK = {"free": 0, "half": 1, "full": 2}


def _band(value: float, free_lt: float | None, half_lt: float | None) -> str:
    if free_lt is not None and value < free_lt:
        return "free"
    if half_lt is not None and value < half_lt:
        return "half"
    return "full"


def judge_ticket(rule: dict, age: int, height_m: float) -> tuple[str, str]:
    """返回 (free|half|full, 触发说明)。"""
    mode = rule.get("mode") or "height"
    height_result = _band(height_m, rule.get("free_height_m"), rule.get("half_height_m"))
    age_result = _band(float(age), _as_float(rule.get("free_age_lt")), _as_float(rule.get("half_age_lt")))

    if mode == "height":
        return height_result, _clause(rule, "clause_ticket", "按身高带判定")
    if mode == "age":
        return age_result, _clause(rule, "clause_ticket", "按年龄判定")
    if mode == "either":
        chosen = height_result if _RANK[height_result] <= _RANK[age_result] else age_result
        return chosen, _clause(rule, "clause_ticket", "身高或年龄满足其一")
    if mode == "both":
        if height_result == "full" or age_result == "full":
            return "full", _clause(rule, "clause_ticket", "身高和年龄必须同时满足，缺一按全票")
        chosen = height_result if _RANK[height_result] >= _RANK[age_result] else age_result
        return chosen, _clause(rule, "clause_ticket", "身高和年龄同时落入优惠带")
    raise ValueError(f"未知判定方式: {mode}")


def judge_benefits(rule: dict, selected: list[str]) -> dict:
    catalog = {item["id"]: item for item in rule.get("benefits") or []}
    blocked: list[str] = []
    notes: list[str] = []
    for item_id in selected:
        item = catalog.get(item_id)
        if not item:
            continue
        for other in item.get("excludes") or []:
            if other in selected:
                blocked.append(other)
                notes.append(f"{item.get('label', item_id)} 与 {catalog.get(other, {}).get('label', other)} 不能叠加")
    return {
        "ok": not notes,
        "blocked": sorted(set(blocked)),
        "notes": notes,
        "clause": _clause(rule, "clause_benefit", "未写互斥条款"),
    }


def judge_promo(rule: dict, ticket: str) -> dict:
    claims_free = bool(rule.get("promo_claims_free"))
    conflict = claims_free and ticket != "free"
    bundle_only = bool(rule.get("bundle_only"))
    return {
        "conflict": conflict or bundle_only,
        "claims_free": claims_free,
        "bundle_only": bundle_only,
        "actual_ticket": ticket,
        "onsale_note": rule.get("onsale_note") or "",
        "clause": _clause(rule, "clause_onsale", ""),
    }


def release_text(rule: dict) -> str:
    days = rule.get("release_days_ahead")
    clock = rule.get("release_clock")
    extra = rule.get("no_show_note") or ""
    if days is None and not clock:
        return "页面未写放票时刻"
    parts = []
    if days is not None and clock:
        parts.append(f"提前 {days} 天，每日 {clock} 放票")
    elif clock:
        parts.append(f"每日 {clock} 放票")
    elif days is not None:
        parts.append(f"最早提前 {days} 天可订")
    if extra:
        parts.append(extra)
    return "。".join(parts)


def run_rule(rule: dict, age: int, height_m: float, benefits: list[str] | None = None) -> dict:
    ticket, ticket_clause = judge_ticket(rule, age, height_m)
    promo = judge_promo(rule, ticket)
    benefit = judge_benefits(rule, benefits or [])
    return {
        "ticket": ticket,
        "ticket_label": TICKET_LABEL[ticket],
        "ticket_clause": ticket_clause,
        "release": release_text(rule),
        "release_clause": _clause(rule, "clause_release", ""),
        "promo": promo,
        "benefits": benefit,
    }


def _as_float(value) -> float | None:
    if value is None:
        return None
    return float(value)


def _clause(rule: dict, key: str, fallback: str) -> str:
    text = (rule.get(key) or "").strip()
    return text or fallback
