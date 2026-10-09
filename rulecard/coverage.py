"""规则覆盖率：票务相关句子有多少被槽位引用过。"""

from __future__ import annotations

from rulecard.segment import segment


def rule_coverage(page_text: str, rule: dict) -> dict:
    clauses = segment(page_text or "")
    ticketish = [row for row in clauses if "ticket" in row["labels"] or "release" in row["labels"] or "sale" in row["labels"] or "benefit" in row["labels"]]
    if not ticketish:
        return {"ratio": 1.0, "total": 0, "covered": 0, "uncovered": []}

    cited = " ".join(
        str(rule.get(key) or "")
        for key in ("clause_ticket", "clause_release", "clause_benefit", "clause_onsale", "onsale_note", "no_show_note")
    )
    covered_rows = []
    uncovered = []
    for row in ticketish:
        text = row["text"]
        hit = text in cited or any(token and token in cited for token in _tokens(text))
        if hit:
            covered_rows.append(row)
        else:
            uncovered.append(text)

    total = len(ticketish)
    covered = len(covered_rows)
    ratio = round(covered / total, 3) if total else 1.0
    return {"ratio": ratio, "total": total, "covered": covered, "uncovered": uncovered}


def _tokens(text: str) -> list[str]:
    # 取较长片段，避免单字误伤
    parts = []
    for size in (12, 8, 6):
        if len(text) >= size:
            parts.append(text[:size])
            break
    return parts
