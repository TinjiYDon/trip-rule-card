"""一轮结构修补。只改自相矛盾的字段，不补页面里没写的数字。"""

from __future__ import annotations

from rulecard.schema_check import validate_rule


def repair_rule(rule: dict, page_text: str) -> tuple[dict, list[str]]:
    fixed = dict(rule)
    notes: list[str] = []
    issues = validate_rule(fixed)
    if "inverted_height" in issues:
        fixed["free_height_m"], fixed["half_height_m"] = fixed["half_height_m"], fixed["free_height_m"]
        notes.append("身高上下界写反，已对调")
    text = page_text or ""
    force_both = any(token in text for token in ("同时满足", "缺一不可", "且"))
    force_either = any(token in text for token in ("二选一", "满足其一", "任一"))
    if force_both and fixed.get("mode") != "both":
        fixed["mode"] = "both"
        notes.append("页面写了合取，判定方式改回同时满足")
    elif force_either and fixed.get("mode") not in ("either", "both"):
        fixed["mode"] = "either"
        notes.append("页面写了析取，判定方式改回满足其一")
    return fixed, notes
