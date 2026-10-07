"""错因。评测和演示用同一套名字。"""

from __future__ import annotations

LABELS = {
    "promo_conflict": "种草冲突",
    "dual_threshold": "双门槛",
    "bundle": "仅售套票",
    "no_threshold": "没有可执行门槛",
    "compile_miss": "编译未对上标注",
    "release_miss": "放票时刻没读到",
    "schema_issue": "结构校验未通过",
}


def classify(
    page_text: str,
    rule: dict,
    compiled_ticket: str,
    ablation_ticket: str,
    gold_ticket: str | None,
    schema_issues: list[str] | None = None,
) -> list[str]:
    tags: list[str] = []
    if schema_issues:
        tags.append("schema_issue")
    has_height = rule.get("free_height_m") is not None or rule.get("half_height_m") is not None
    has_age = rule.get("free_age_lt") is not None or rule.get("half_age_lt") is not None
    if not has_height and not has_age:
        tags.append("no_threshold")
    if rule.get("promo_claims_free") and compiled_ticket != "free":
        tags.append("promo_conflict")
    if rule.get("mode") == "both" and ablation_ticket != compiled_ticket:
        tags.append("dual_threshold")
    if rule.get("bundle_only"):
        tags.append("bundle")
    mentions_release = any(token in (page_text or "") for token in ("放票", "预约", "预订", "日前", "开售"))
    if mentions_release and not rule.get("release_clock") and rule.get("release_days_ahead") is None:
        tags.append("release_miss")
    if gold_ticket and compiled_ticket != gold_ticket:
        tags.append("compile_miss")
    return tags
