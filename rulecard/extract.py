"""从票务散文抽出可执行规则。

默认不调用大模型。现场没网时，这条流水线仍然能跑。
大模型只允许作为可选草案，不能跳过本模块的结构校验。
"""

from __future__ import annotations

import re

_MODES = ("height", "age", "either", "both")


def extract_rule(page_text: str, promo_text: str = "") -> dict:
    text = _normalize(page_text)
    promo = _normalize(promo_text)
    mode = _mode(text)
    free_h, half_h = _heights(text)
    free_age, half_age = _ages(text)
    days = _first_int(r"提前\s*(\d+)\s*天", text)
    if days is None:
        days = _first_int(r"(\d+)\s*日前", text)
    clock = _clock(text)
    bundle_only = any(token in text for token in ("仅售套票", "不卖散票", "散客大门票已下架", "单独大门票"))
    return {
        "mode": mode,
        "free_height_m": free_h,
        "half_height_m": half_h,
        "free_age_lt": free_age,
        "half_age_lt": half_age,
        "release_days_ahead": days,
        "release_clock": clock,
        "no_show_note": _no_show(text),
        "bundle_only": bundle_only,
        "promo_claims_free": ("免费" in promo) or ("免票" in promo),
        "onsale_note": _onsale_note(text, bundle_only),
        "benefits": _benefits(text),
        "clause_ticket": _ticket_clause(text),
        "clause_release": _sentence_with(text, ("放票", "预约", "日前")),
        "clause_benefit": _sentence_with(text, ("不能叠加", "不可同时", "学生票")),
        "clause_onsale": _sentence_with(text, ("套票", "散票", "下架", "元")),
    }


def _normalize(text: str) -> str:
    return (
        text.replace("（", "(")
        .replace("）", ")")
        .replace("．", ".")
        .replace("：", ":")
        .replace("米", "米")
    )


def _mode(text: str) -> str:
    if "同时满足" in text or "缺一不可" in text or "并且" in text and "周岁" in text and "米" in text:
        if "同时满足" in text or "缺一不可" in text:
            return "both"
    if "二选一" in text or "满足其一" in text or "任一" in text:
        return "either"
    has_height = "米" in text and re.search(r"\d+(?:\.\d+)?\s*米", text)
    has_age = "周岁" in text
    if has_age and not has_height:
        return "age"
    if has_height and not has_age:
        return "height"
    if "不以身高" in text:
        return "age"
    return "height" if has_height else "age"


def _heights(text: str) -> tuple[float | None, float | None]:
    free = None
    half = None
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*米(?:\(含\)|以下|不满)?", text):
        value = float(match.group(1))
        window = text[max(0, match.start() - 8) : match.end() + 12]
        if any(token in window for token in ("免", "免费")) or "以下免" in window:
            free = value if free is None else min(free, value)
        elif "半" in window:
            half = value if half is None else max(half, value)
    # 「1.2米至1.4米半票」里 1.4 常是半票上界
    span = re.search(r"(\d+(?:\.\d+)?)\s*米(?:以上)?至\s*(\d+(?:\.\d+)?)\s*米半", text)
    if span:
        half = float(span.group(2))
        if free is None:
            free = float(span.group(1))
    under = re.search(r"不满\s*(\d+(?:\.\d+)?)\s*米免", text)
    if under:
        free = float(under.group(1))
    half_under = re.search(r"(\d+(?:\.\d+)?)\s*米以下半", text)
    if half_under:
        half = float(half_under.group(1))
    return free, half


def _ages(text: str) -> tuple[int | None, int | None]:
    free = None
    half = None
    patterns = (
        r"(?:未满|不满)\s*(\d+)\s*周岁",
        r"(\d+)\s*周岁以下",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            age = int(match.group(1))
            tail = text[match.end() : match.end() + 18]
            window = text[match.start() : match.end() + 18]
            if "免" in window or "免" in tail:
                free = age
            elif "半" in window:
                half = age
            elif half is None and free != age:
                half = age
    return free, half


def _clock(text: str) -> str | None:
    match = re.search(r"(\d{1,2}:\d{2})", text)
    return match.group(1) if match else None


def _first_int(pattern: str, text: str) -> int | None:
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _no_show(text: str) -> str:
    if "未履约" in text or "爽约" in text:
        return _sentence_with(text, ("未履约", "爽约"))
    return ""


def _onsale_note(text: str, bundle_only: bool) -> str:
    if bundle_only:
        return _sentence_with(text, ("套票", "下架", "散票")) or "仅售套票"
    return ""


def _benefits(text: str) -> list[dict]:
    items = []
    if "学生" in text and ("不能叠加" in text or "不可同时" in text):
        items.append({"id": "student", "label": "学生优惠", "excludes": ["child"]})
        items.append({"id": "child", "label": "儿童优惠", "excludes": ["student"]})
    return items


def _ticket_clause(text: str) -> str:
    preferred = _sentence_with(text, ("二选一", "同时满足", "缺一不可", "满足其一"))
    if preferred:
        return preferred
    return _sentence_with(text, ("免票", "半票", "免费", "周岁", "米"))


def _sentence_with(text: str, tokens: tuple[str, ...]) -> str:
    chunks = re.split(r"[。\n]", text)
    for chunk in chunks:
        if any(token in chunk for token in tokens):
            return chunk.strip()
    return ""
