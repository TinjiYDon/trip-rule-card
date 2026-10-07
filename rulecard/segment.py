"""把票务页切成带标签的句子。后面的抽取和轨迹都引用这里的切分。"""

from __future__ import annotations

import re

_TICKET = ("免", "半", "优惠", "周岁", "米", "厘米", "全票")
_RELEASE = ("放票", "预约", "预订", "开售", "日前")
_BENEFIT = ("不能叠加", "不可同时", "学生")
_SALE = ("套票", "散票", "下架", "单人票")


def segment(page_text: str) -> list[dict]:
    text = page_text.replace("；", "。").replace(";", "。")
    chunks = [chunk.strip() for chunk in re.split(r"[。\n]", text) if chunk.strip()]
    rows = []
    for index, chunk in enumerate(chunks):
        labels = []
        if any(token in chunk for token in _TICKET):
            labels.append("ticket")
        if any(token in chunk for token in _RELEASE):
            labels.append("release")
        if any(token in chunk for token in _BENEFIT):
            labels.append("benefit")
        if any(token in chunk for token in _SALE):
            labels.append("sale")
        if not labels:
            labels.append("noise")
        rows.append({"index": index, "text": chunk, "labels": labels})
    return rows
