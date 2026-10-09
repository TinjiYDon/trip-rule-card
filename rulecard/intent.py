"""对话意图：把一句话收成景区 + 出行人画像，减少点选。"""

from __future__ import annotations

import re

from rulecard.load import list_venues

_VENUE_ALIASES = (
    (("科技馆", "科学技术馆", "cstm"), "tech-museum"),
    (("故宫", "紫禁城", "博物院"), "gugong"),
    (("国博", "国家博物馆", "chnmuseum"), "chnmuseum"),
    (("东方明珠", "明珠", "登塔"), "oriental-pearl"),
    (("上博", "上海博物馆", "特展"), "shanghai-museum"),
)

_FAMILY = {
    "一家三口": [("成人", 35, 1.7), ("儿童", 7, 1.3), ("幼童", 5, 1.1)],
    "三口": [("成人", 35, 1.7), ("儿童", 7, 1.3), ("幼童", 5, 1.1)],
    "亲子": [("成人", 35, 1.7), ("儿童", 7, 1.3)],
    "带娃": [("成人", 35, 1.7), ("儿童", 7, 1.3)],
    "两个人": [("成人", 35, 1.7), ("儿童", 7, 1.3)],
    "本人": [("成人", 28, 1.7)],
    "自己": [("成人", 28, 1.7)],
}


def parse_intent(text: str, venues: list[dict] | None = None) -> dict:
    raw = (text or "").strip()
    venues = venues if venues is not None else list_venues()
    venue_id = _match_venue(raw, venues)
    travelers = _match_family(raw)
    ages = [int(x) for x in re.findall(r"(\d+)\s*岁", raw)]
    heights = [float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*米", raw)]
    if ages or heights:
        travelers = _merge_measures(travelers, ages, heights)
    if not travelers:
        travelers = _named_travelers([("成人", 35, 1.7), ("儿童", 7, 1.3)])
    reply = _reply(raw, venue_id, travelers, venues)
    return {
        "venue_id": venue_id,
        "travelers": travelers,
        "reply": reply,
        "raw": raw,
    }


def _match_venue(text: str, venues: list[dict]) -> str | None:
    for aliases, venue_id in _VENUE_ALIASES:
        if any(alias in text for alias in aliases):
            if any(v["id"] == venue_id for v in venues):
                return venue_id
    # 直接点名馆名
    for venue in venues:
        if venue["name"] and venue["name"] in text:
            return venue["id"]
    return None


def _match_family(text: str) -> list[dict]:
    for key, members in _FAMILY.items():
        if key in text:
            return _named_travelers(members)
    if "孩子" in text or "小孩" in text or "儿童" in text:
        return _named_travelers([("成人", 35, 1.7), ("儿童", 7, 1.3)])
    return []


def _named_travelers(members: list[tuple[str, int, float]]) -> list[dict]:
    counts: dict[str, int] = {}
    rows = []
    for role, age, height in members:
        counts[role] = counts.get(role, 0) + 1
        rows.append(
            {
                "id": f"{role}{counts[role]}",
                "name": f"{role}{counts[role]}",
                "age": age,
                "height_m": height,
                "tags": [],
            }
        )
    return rows


def _merge_measures(travelers: list[dict], ages: list[int], heights: list[float]) -> list[dict]:
    if not travelers:
        n = max(len(ages), len(heights), 1)
        travelers = _named_travelers([("出行人", 7, 1.3)] * n)
    for index, person in enumerate(travelers):
        if index < len(ages):
            person["age"] = ages[index]
        if index < len(heights):
            person["height_m"] = heights[index]
    return travelers


def _reply(text: str, venue_id: str | None, travelers: list[dict], venues: list[dict]) -> str:
    name = next((v["name"] for v in venues if v["id"] == venue_id), None)
    who = "、".join(f"{t['name']}({t['age']}岁/{t['height_m']}米)" for t in travelers)
    if venue_id and name:
        return f"好的，按「{name}」给 {who} 算票。条款我已带入，你不用再粘贴。"
    if venue_id is None:
        return f"我先按 {who} 准备出行人。再说一下去哪个馆（科技馆/故宫/国博/东方明珠/上博）？"
    return f"已记下 {who}。"
