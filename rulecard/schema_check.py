"""结构校验。抽出来的规则必须先过这一层，执行器不接受残缺结构。"""

from __future__ import annotations

MODES = ("height", "age", "either", "both")


def validate_rule(rule: dict) -> list[str]:
    issues: list[str] = []
    if rule.get("mode") not in MODES:
        issues.append("mode")
    free_h = rule.get("free_height_m")
    half_h = rule.get("half_height_m")
    if free_h is not None and half_h is not None and float(free_h) > float(half_h):
        issues.append("inverted_height")
    if rule.get("mode") == "both":
        has_height = free_h is not None or half_h is not None
        has_age = rule.get("free_age_lt") is not None or rule.get("half_age_lt") is not None
        if not has_height or not has_age:
            issues.append("incomplete_both")
    for key in ("free_height_m", "half_height_m"):
        if rule.get(key) is not None and float(rule[key]) <= 0:
            issues.append("bad_height")
    return issues
