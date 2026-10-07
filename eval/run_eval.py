"""评测：直接问（关键词对照）对编译后执行。评测同学只改本目录。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rulecard.execute import TICKET_LABEL
from rulecard.load import list_venues
from rulecard.pipeline import compile_and_run


def main() -> None:
    rows = []
    for venue in list_venues():
        gold = venue["gold"]
        result = compile_and_run(venue, gold["age"], gold["height_m"])
        rows.append(
            {
                "id": venue["id"],
                "split": venue["split"],
                "gold": gold["ticket"],
                "baseline": result["baseline_ticket"],
                "compiled": result["compiled"]["ticket"],
                "baseline_correct": result["baseline_correct"],
                "compiled_correct": result["compiled_correct"],
                "clause": result["compiled"]["ticket_clause"],
            }
        )
    report = _summarize(rows)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    out = Path(__file__).with_name("latest.json")
    out.write_text(text, encoding="utf-8")
    print(text)
    print("票种中文:", TICKET_LABEL)


def _summarize(rows: list[dict]) -> dict:
    def rate(items: list[dict], key: str) -> float | None:
        if not items:
            return None
        return round(sum(1 for row in items if row[key]) / len(items), 3)

    heldout = [row for row in rows if row["split"] == "heldout"]
    return {
        "n": len(rows),
        "baseline_accuracy": rate(rows, "baseline_correct"),
        "compiled_accuracy": rate(rows, "compiled_correct"),
        "heldout_n": len(heldout),
        "heldout_baseline_accuracy": rate(heldout, "baseline_correct"),
        "heldout_compiled_accuracy": rate(heldout, "compiled_correct"),
        "rows": rows,
        "note": "种子集含未核验馆。准确率只说明抽取器相对关键词对照的差距，不能写成全国投诉统计。",
    }


if __name__ == "__main__":
    main()
