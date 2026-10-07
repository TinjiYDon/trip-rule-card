"""两种朴素读法，用来对照编译执行。

只看种草：广告里出现免票或半票就下结论。
只读首个数：文中第一个周岁或第一个米，小于就当免票，不读半票、不读第二个门槛。
消融在 flow 里：槽位相同，但把「同时满足」改成「满足其一」。
这三路都不是已经调用的大模型。
"""

from __future__ import annotations

import re

from rulecard.execute import judge_ticket
from rulecard.extract import extract_rule, prepare_text


def keyword_ticket(promo_text: str, page_text: str = "") -> tuple[str, str]:
    if any(token in promo_text for token in ("免费", "免票", "全免")):
        return "free", "种草里出现免票，直接采信"
    if "半票" in promo_text or "半价" in promo_text:
        return "half", "种草里出现半票，直接采信"
    if "免费" in page_text or "免票" in page_text:
        return "free", "种草没写，就在页面里看到免票"
    return "full", "没看到优惠词，当成全票"


def first_number_ticket(page_text: str, age: int, height_m: float) -> tuple[str, str]:
    text = prepare_text(page_text)
    age_match = re.search(r"(\d+)\s*周岁", text)
    height_match = re.search(r"(\d+(?:\.\d+)?)\s*米", text)
    if age_match and height_match:
        use_age = age_match.start() < height_match.start()
    elif age_match:
        use_age = True
    elif height_match:
        use_age = False
    else:
        return "full", "页面没有数字门槛"
    if use_age:
        bound = int(age_match.group(1))
        if age < bound:
            return "free", f"只读第一个年龄 {bound} 周岁，小于就当免票"
        return "full", f"只读第一个年龄 {bound} 周岁，不小于就当全票"
    bound = float(height_match.group(1))
    if height_m < bound:
        return "free", f"只读第一个身高 {bound} 米，小于就当免票"
    return "full", f"只读第一个身高 {bound} 米，不小于就当全票"


def drop_and_ticket(page_text: str, promo_text: str, age: int, height_m: float) -> tuple[str, str]:
    rule = extract_rule(page_text, promo_text)
    if rule.get("mode") == "both":
        ticket, _ = judge_ticket({**rule, "mode": "either"}, age, height_m)
        return ticket, "消融：数字相同，同时满足被改成满足其一"
    ticket, _ = judge_ticket(rule, age, height_m)
    return ticket, "这页不是合取规则，消融与编译相同"
