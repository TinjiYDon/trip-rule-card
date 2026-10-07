"""从票务散文抽出可执行规则。

默认不调用大模型。现场没网时，这条流水线仍然能跑。
"""

from __future__ import annotations

import re

_CN = "一二三四五六七八九"


def prepare_text(text: str) -> str:
    normalized = (
        (text or "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("．", ".")
        .replace("：", ":")
    )
    normalized = re.sub(r"(\d+)\s*厘米", lambda match: f"{int(match.group(1)) / 100:.2f}米", normalized)

    def _spoken_meter(match: re.Match) -> str:
        whole = _CN.index(match.group(1)) + 1
        frac = _CN.index(match.group(2)) + 1
        return f"{whole}.{frac}米"

    return re.sub(rf"([{_CN}])米([{_CN}])", _spoken_meter, normalized)


def extract_rule(page_text: str, promo_text: str = "") -> dict:
    text = prepare_text(page_text)
    promo = prepare_text(promo_text)
    free_h, half_h, free_h_incl, half_h_incl = _heights(text)
    free_age, half_age, free_age_incl, half_age_incl = _ages(text)
    days = _first_int(r"提前\s*(\d+)\s*天", text)
    if days is None:
        days = _first_int(r"(\d+)\s*日前", text)
    bundle_only = any(token in text for token in ("仅售套票", "不卖散票", "散客大门票已下架", "单独大门票"))
    return {
        "mode": _mode(text),
        "free_height_m": free_h,
        "half_height_m": half_h,
        "free_age_lt": free_age,
        "half_age_lt": half_age,
        "free_height_inclusive": free_h_incl,
        "half_height_inclusive": half_h_incl,
        "free_age_inclusive": free_age_incl,
        "half_age_inclusive": half_age_incl,
        "release_days_ahead": days,
        "release_clock": _clock(text),
        "no_show_note": _no_show(text),
        "bundle_only": bundle_only,
        "promo_claims_free": any(token in promo for token in ("免费", "免票", "全免")),
        "onsale_note": _onsale_note(text, bundle_only),
        "benefits": _benefits(text),
        "clause_ticket": _ticket_clause(text),
        "clause_release": _sentence_with(text, ("放票", "预约", "预订", "日前", "开售")),
        "clause_benefit": _sentence_with(text, ("不能叠加", "不可同时", "学生票")),
        "clause_onsale": _sentence_with(text, ("套票", "散票", "下架", "元")),
    }


def _mode(text: str) -> str:
    has_height = bool(re.search(r"\d+(?:\.\d+)?\s*米", text))
    has_age = "周岁" in text
    both = any(token in text for token in ("同时满足", "缺一不可", "且"))
    either = any(token in text for token in ("二选一", "满足其一", "任一", "或"))
    if both and has_height and has_age:
        return "both"
    if either and has_height and has_age:
        return "either"
    if has_age and not has_height:
        return "age"
    if "不以身高" in text and has_age:
        return "age"
    if has_height and not has_age:
        return "height"
    return "height" if has_height else "age"


def _heights(text: str) -> tuple[float | None, float | None, bool, bool]:
    free = None
    half = None
    free_incl = False
    half_incl = False
    for match in re.finditer(r"(\d+(?:\.\d+)?)\s*米", text):
        value = float(match.group(1))
        after = text[match.end() : match.end() + 8]
        local = text[max(0, match.start() - 6) : match.end() + 12]
        sentence = _sentence_at(text, match.start())
        kind = _kind(local, sentence)
        inclusive = "含" in after
        if kind == "free" and free is None:
            free = value
            free_incl = inclusive
        elif kind == "half":
            half = value if half is None else max(half, value)
            half_incl = inclusive or half_incl
    span = re.search(r"(\d+(?:\.\d+)?)\s*米(?:以上)?至\s*(\d+(?:\.\d+)?)\s*米半", text)
    if span:
        half = float(span.group(2))
        if free is None:
            free = float(span.group(1))
    under = re.search(r"(?:不满|不到|不足)\s*(\d+(?:\.\d+)?)\s*米(?:免|不收)", text)
    if under:
        free = float(under.group(1))
    half_under = re.search(r"(\d+(?:\.\d+)?)\s*米以下半", text)
    if half_under:
        half = float(half_under.group(1))
    return free, half, free_incl, half_incl


def _ages(text: str) -> tuple[int | None, int | None, bool, bool]:
    free = None
    half = None
    free_incl = False
    half_incl = False
    pattern = r"(?:未满|不满|不足|不到)?\s*(\d+)\s*周岁(?:\s*\(含\))?(?:\s*以下)?"
    for match in re.finditer(pattern, text):
        age = int(match.group(1))
        after = text[match.end() : match.end() + 6]
        local = text[max(0, match.start() - 8) : match.end() + 16]
        sentence = _sentence_at(text, match.start())
        kind = _kind(local, sentence)
        inclusive = "含" in text[match.start() : match.end() + 6] or "含" in after
        if kind == "free" and free is None:
            free = age
            free_incl = inclusive
        elif kind == "half" and half is None:
            half = age
            half_incl = inclusive
    return free, half, free_incl, half_incl


def _kind(local: str, sentence: str) -> str | None:
    if "半" in local:
        return "half"
    if any(token in local for token in ("免", "不收", "免费")):
        return "free"
    if "优惠" in local and "免" not in local:
        return "half"
    if any(token in sentence for token in ("免", "不收", "免费")) and "半" not in sentence and "优惠" not in sentence:
        return "free"
    if "半" in sentence or ("优惠" in sentence and "免" not in sentence):
        return "half"
    return None


def _sentence_at(text: str, index: int) -> str:
    start = max(text.rfind("。", 0, index), text.rfind("\n", 0, index)) + 1
    end_candidates = [pos for pos in (text.find("。", index), text.find("\n", index)) if pos >= 0]
    end = min(end_candidates) if end_candidates else len(text)
    return text[start:end]


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
    if "学生" in text and ("不能叠加" in text or "不可同时" in text):
        return [
            {"id": "student", "label": "学生优惠", "excludes": ["child"]},
            {"id": "child", "label": "儿童优惠", "excludes": ["student"]},
        ]
    return []


def _ticket_clause(text: str) -> str:
    preferred = _sentence_with(text, ("二选一", "同时满足", "缺一不可", "满足其一", "且"))
    if preferred:
        return preferred
    return _sentence_with(text, ("免票", "半票", "免费", "优惠", "周岁", "米"))


def _sentence_with(text: str, tokens: tuple[str, ...]) -> str:
    for chunk in re.split(r"[。\n]", text):
        if any(token in chunk for token in tokens):
            return chunk.strip()
    return ""
