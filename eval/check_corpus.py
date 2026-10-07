"""语料健全性检查。标注同学加馆后先跑这个，再进评测。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rulecard.extract import extract_rule
from rulecard.load import list_venues
from rulecard.schema_check import validate_rule

REQUIRED = ("id", "name", "city", "split", "verified", "source", "page_text", "promo_text", "gold")


def check() -> list[dict]:
    problems: list[dict] = []
    seen: set[str] = set()
    for venue in list_venues():
        venue_id = venue.get("id") or venue.get("_file")
        missing = [key for key in REQUIRED if key not in venue]
        if missing:
            problems.append({"id": venue_id, "problem": f"缺字段 {missing}"})
        if venue_id in seen:
            problems.append({"id": venue_id, "problem": "id 重复"})
        seen.add(venue_id)
        if venue.get("split") not in ("train", "heldout"):
            problems.append({"id": venue_id, "problem": "split 只能是 train 或 heldout"})
        if venue.get("verified") and not (venue.get("source") or "").startswith("http"):
            problems.append({"id": venue_id, "problem": "已核对但没有 URL 出处"})
        gold = venue.get("gold")
        if gold is not None and gold.get("ticket") not in ("free", "half", "full"):
            problems.append({"id": venue_id, "problem": "gold.ticket 只能是 free/half/full"})
        issues = validate_rule(extract_rule(venue.get("page_text") or "", ""))
        if issues:
            problems.append({"id": venue_id, "problem": f"抽出的结构未过校验 {issues}"})
    return problems


def main() -> None:
    problems = check()
    venues = list_venues()
    heldout = [v for v in venues if v.get("split") == "heldout"]
    verified = [v for v in venues if v.get("verified")]
    report = {
        "venues": len(venues),
        "heldout": len(heldout),
        "verified": len(verified),
        "problems": problems,
        "ok": not problems,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if problems:
        sys.exit(1)


if __name__ == "__main__":
    main()
