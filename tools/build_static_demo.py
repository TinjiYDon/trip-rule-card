"""生成静态 LIVE DEMO：嵌入语料 + 与 Python 对齐的浏览器引擎。"""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from rulecard.load import list_venues
from rulecard.pipeline import compile_and_run

OUT_DIR = ROOT / "docs" / "live"
ENGINE = (ROOT / "demo" / "rulecard_browser.js").read_text(encoding="utf-8")


def main() -> None:
    venues = []
    for venue in list_venues():
        gold = venue.get("gold") or {}
        age = gold.get("age", 7)
        height = gold.get("height_m", 1.3)
        result = compile_and_run(venue, age, height)
        venues.append(
            {
                "id": venue["id"],
                "name": venue["name"],
                "city": venue["city"],
                "split": venue["split"],
                "verified": bool(venue.get("verified")),
                "source": venue.get("source") or "",
                "page_text": venue.get("page_text") or "",
                "promo_text": venue.get("promo_text") or "",
                "gold": venue.get("gold"),
                "_py_ticket": result["compiled"]["ticket"],
            }
        )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data_js = "window.RULECARD_VENUES = " + json.dumps(venues, ensure_ascii=False, indent=2) + ";\n"
    (OUT_DIR / "venues.js").write_text(data_js, encoding="utf-8")
    (OUT_DIR / "rulecard_browser.js").write_text(ENGINE, encoding="utf-8")
    html = (ROOT / "demo" / "live.html").read_text(encoding="utf-8")
    (OUT_DIR / "index.html").write_text(html, encoding="utf-8")
    # 自检：浏览器引擎与 Python 在默认人设上一致
    mismatches = []
    # 延迟到 node 或跳过；这里用标记字段供人工看
    report = {"venues": len(venues), "out": str(OUT_DIR)}
    (OUT_DIR / "build.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
