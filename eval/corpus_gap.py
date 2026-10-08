"""语料缺口报告：把docs/分工.md 的目标换算成还差多少。

分工.md 给标注同学（A）的目标是「约 30 条，其中约 8 条 heldout」，
并且强调「已核对官网的才能写成现行票价」。但目标写在文档里，
每次提交后要靠人肉数json 文件才能知道还差多少。

这个脚本只读语料，不改语料，也不生成任何票务内容 —— 它只回答
「离目标还差几条、哪些条verified=false 需要换官网原文、哪些 heldout
没有标注」。票价必须由标注同学从当天官网原文抄进来，本工具不会
替任何人补数据。

用法：
    python eval/corpus_gap.py            # 人读摘要
    python eval/corpus_gap.py --json     # 机器可读
退出码：达标为 0，未达标为 1（可直接接进 CI 或 pre-commit）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rulecard.load import list_venues

# 与 docs/分工.md 中 A 标注一栏一致
TARGET_TOTAL = 30
TARGET_HELDOUT = 8


def build_report() -> dict:
    venues = list_venues()
    total = len(venues)
    heldout = [v for v in venues if v.get("split") == "heldout"]
    verified = [v for v in venues if v.get("verified")]

    def vid(v: dict) -> str:
        return str(v.get("id") or v.get("_file") or "?")

    unverified = [
        {"id": vid(v), "name": v.get("name"), "split": v.get("split")}
        for v in venues
        if not v.get("verified")
    ]
    heldout_no_gold = [
        {"id": vid(v), "name": v.get("name")}
        for v in heldout
        if not (v.get("gold") or {}).get("ticket")
    ]
    # heldout 不足时，train 里的verified 条目是最省力的替补来源
    # （已经是官网原文，只需改 split，一个字段的事）
    promote_candidates = [
        {"id": vid(v), "name": v.get("name"), "has_gold": bool((v.get("gold") or {}).get("ticket"))}
        for v in verified
        if v.get("split") != "heldout"
    ]

    return {
        "target": {"total": TARGET_TOTAL, "heldout": TARGET_HELDOUT},
        "current": {
            "total": total,
            "heldout": len(heldout),
            "verified": len(verified),
            "scored": sum(1 for v in venues if (v.get("gold") or {}).get("ticket")),
        },
        "gap": {
            "total": max(TARGET_TOTAL - total, 0),
            "heldout": max(TARGET_HELDOUT - len(heldout), 0),
            "unverified": len(unverified),
        },
        "need_official_source": unverified,
        "heldout_missing_gold": heldout_no_gold,
        "promote_to_heldout": promote_candidates,
        "done": (
            total >= TARGET_TOTAL
            and len(heldout) >= TARGET_HELDOUT
            and not heldout_no_gold
        ),
    }


def render(rep: dict) -> str:
    cur, gap, tgt = rep["current"], rep["gap"], rep["target"]
    lines: list[str] = []
    lines.append("语料缺口报告（目标来自 docs/分工.md · A 标注）")
    lines.append("=" * 52)
    lines.append(
        f"总条数   {cur['total']:>3} / {tgt['total']}   缺口 {gap['total']}"
    )
    lines.append(
        f"heldout  {cur['heldout']:>3} / {tgt['heldout']}   缺口 {gap['heldout']}"
    )
    lines.append(
        f"已核官网 {cur['verified']:>3}            待换原文 {gap['unverified']}"
    )
    lines.append(f"有标注   {cur['scored']:>3}（进评测分母的条数）")
    lines.append("")

    if rep["heldout_missing_gold"]:
        lines.append("[必须修] heldout 没有 gold.ticket，不进留出集分母：")
        for item in rep["heldout_missing_gold"]:
            lines.append(f"  - {item['id']}  {item['name']}")
        lines.append("")

    if gap["heldout"] > 0 and rep["promote_to_heldout"]:
        lines.append(f"[省力] 还差 {gap['heldout']} 条 heldout。以下已是官网原文，")
        lines.append("       只需把 split 改成 heldout（一个字段）：")
        for item in rep["promote_to_heldout"]:
            mark = "有标注" if item["has_gold"] else "缺 gold，改split 前需补标注"
            lines.append(f"  - {item['id']}  {item['name']}  [{mark}]")
        lines.append("")

    if gap["unverified"]:
        lines.append(f"[工作量] 以下 {gap['unverified']} 条 verified=false，")
        lines.append("          只能当规则类型例句，不能写成官网现行票价：")
        for item in rep["need_official_source"][:40]:
            lines.append(f"  - {item['id']}  {item['name']}  ({item['split']})")
        if len(rep["need_official_source"]) > 40:
            lines.append(f"  ... 另有 {len(rep['need_official_source']) - 40} 条")
        lines.append("")

    lines.append(
        "达标：全部完成" if rep["done"] else "未达标：按上面三段依次处理"
    )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="语料缺口报告")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    args = ap.parse_args()

    rep = build_report()
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        print(render(rep))
    sys.exit(0 if rep["done"] else 1)


if __name__ == "__main__":
    main()