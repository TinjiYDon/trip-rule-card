"""评测三路读法：只看种草、只读第一个数字、编译后执行。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rulecard.errors import LABELS
from rulecard.load import list_venues
from rulecard.pipeline import compile_and_run


def main() -> None:
    rows = []
    for venue in list_venues():
        gold = venue.get("gold") or {}
        age = gold.get("age", 7)
        height = gold.get("height_m", 1.3)
        result = compile_and_run(venue, age, height)
        rows.append(
            {
                "id": venue["id"],
                "split": venue["split"],
                "verified": bool(venue.get("verified")),
                "gold": result["gold_ticket"],
                "keyword": result["baseline_ticket"],
                "first_number": result["first_number_ticket"],
                "ablation": result["ablation_ticket"],
                "compiled": result["compiled"]["ticket"],
                "keyword_correct": result["baseline_correct"],
                "first_number_correct": result["first_number_correct"],
                "compiled_correct": result["compiled_correct"],
                "errors": result["errors"],
                "mode": result["rule"]["mode"],
            }
        )
    report = _summarize(rows)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    Path(__file__).with_name("latest.json").write_text(text, encoding="utf-8")
    print(text)


def _summarize(rows: list[dict]) -> dict:
    scored = [row for row in rows if row["gold"]]
    heldout = [row for row in scored if row["split"] == "heldout"]
    verified = [row for row in scored if row["verified"]]
    counts: dict[str, int] = {}
    for row in rows:
        for tag in row["errors"]:
            counts[tag] = counts.get(tag, 0) + 1
    return {
        "n_files": len(rows),
        "n_scored": len(scored),
        "keyword_accuracy": _rate(scored, "keyword_correct"),
        "first_number_accuracy": _rate(scored, "first_number_correct"),
        "compiled_accuracy": _rate(scored, "compiled_correct"),
        "heldout_n": len(heldout),
        "heldout_keyword_accuracy": _rate(heldout, "keyword_correct"),
        "heldout_first_number_accuracy": _rate(heldout, "first_number_correct"),
        "heldout_compiled_accuracy": _rate(heldout, "compiled_correct"),
        "verified_n": len(verified),
        "verified_compiled_accuracy": _rate(verified, "compiled_correct"),
        "error_counts": counts,
        "error_labels": LABELS,
        "rows": rows,
        "note": "分母只含有标注票种的馆。立牌页没有数字，不进准确率。已核对馆目前只有故宫和中国科学技术馆。其余是规则类型例句。",
    }


def _rate(items: list[dict], key: str) -> float | None:
    if not items:
        return None
    return round(sum(1 for row in items if row[key]) / len(items), 3)


if __name__ == "__main__":
    main()
