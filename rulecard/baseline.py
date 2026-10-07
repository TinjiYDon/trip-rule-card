"""直接问模型的替身：只看种草里的优惠词，不执行条款。

这是评测里的对照，不是作品本身。它会把「儿童免费」当成结论。
"""

from __future__ import annotations


def baseline_ticket(promo_text: str, page_text: str = "") -> str:
    text = f"{promo_text}\n{page_text}"
    if "免费" in promo_text or "免票" in promo_text:
        return "free"
    if "半票" in promo_text or "半价" in promo_text:
        return "half"
    if "免费" in text:
        return "free"
    return "full"
