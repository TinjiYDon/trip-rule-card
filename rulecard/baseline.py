"""兼容旧评测入口。实现见 direct.keyword_ticket。"""

from rulecard.direct import keyword_ticket


def baseline_ticket(promo_text: str, page_text: str = "") -> str:
    ticket, _ = keyword_ticket(promo_text, page_text)
    return ticket
