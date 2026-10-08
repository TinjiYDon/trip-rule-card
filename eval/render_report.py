"""把评测结果渲染成一页报告，供答辩截图或附在提交里。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LATEST = Path(__file__).with_name("latest.json")
OUT = ROOT / "docs" / "report.html"

TICKET = {"free": "免票", "half": "半票", "full": "全票", None: "无标注"}


def _trace_block(sample: dict) -> str:
    """Render the six-stage trace using flow.compile_and_run's own stage names.

    The demo prints these same strings, so the screenshot and the live run
    cannot drift apart (issue #5).
    """
    if not sample:
        return ""
    stages = sample.get("stages") or []
    steps = "".join(
        f"<li><b>{i}. {stage.get('stage')}</b>"
        f"<span>{stage.get('summary') or ''}</span>"
        f"<em>{stage.get('detail') or ''}</em></li>"
        for i, stage in enumerate(stages, 1)
    )
    return f"""<h2>六步轨迹 · {sample.get('name') or sample.get('id')}</h2>
<p class="note">步骤名取自 <code>rulecard/flow.py</code>，与演示页逐字相同。</p>
<ol class="trace">{steps}</ol>
<p class="note">该馆三路读法：种草 {TICKET.get(sample.get('keyword'))} ·
首个数 {TICKET.get(sample.get('first_number'))} ·
消融 {TICKET.get(sample.get('ablation'))} ·
编译执行 <b>{TICKET.get(sample.get('compiled'))}</b>
（已核对官网：{'是' if sample.get('verified') else '否，规则类型例句'}）</p>"""


def main() -> None:
    data = json.loads(LATEST.read_text(encoding="utf-8"))
    labels = data.get("error_labels") or {}
    counts = data.get("error_counts") or {}
    rows = data.get("rows") or []
    bars = "".join(
        f'<div class="bar"><span>{labels.get(tag, tag)}</span>'
        f'<i style="width:{count * 36}px"></i><b>{count}</b></div>'
        for tag, count in sorted(counts.items(), key=lambda item: -item[1])
    ) or "<p>没有错因。</p>"
    table = "".join(
        "<tr>"
        f"<td>{row['id']}</td><td>{row['split']}</td>"
        f"<td>{'已核对' if row['verified'] else '例句'}</td>"
        f"<td>{TICKET.get(row['gold'])}</td>"
        f"<td>{TICKET.get(row['keyword'])}</td>"
        f"<td>{TICKET.get(row['first_number'])}</td>"
        f"<td class='compiled'>{TICKET.get(row['compiled'])}</td>"
        f"<td>{'、'.join(labels.get(t, t) for t in row['errors']) or '—'}</td>"
        "</tr>"
        for row in rows
    )
    html = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>规则卡评测报告</title>
<style>
body {{ font-family: "Microsoft YaHei", sans-serif; margin: 32px; color: #172033; }}
h1 {{ font-size: 22px; }}
.cards {{ display: flex; gap: 12px; margin: 16px 0; flex-wrap: wrap; }}
.card {{ border: 1px solid #e4e8ef; border-radius: 10px; padding: 12px 16px; }}
.card b {{ display: block; font-size: 24px; color: #124ea2; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 16px; }}
td, th {{ border: 1px solid #e4e8ef; padding: 6px 8px; text-align: left; }}
.compiled {{ font-weight: 700; }}
.bar {{ display: flex; align-items: center; gap: 8px; margin: 4px 0; font-size: 13px; }}
.bar span {{ width: 130px; }}
.bar i {{ display: inline-block; height: 12px; background: #124ea2; border-radius: 6px; min-width: 4px; }}
.note {{ color: #5c6778; font-size: 12px; margin-top: 16px; }}
ol.trace {{ margin: 8px 0 0; padding-left: 0; list-style: none; }}
ol.trace li {{ display: grid; grid-template-columns: 96px 160px 1fr; gap: 10px;
  align-items: baseline; font-size: 13px; padding: 7px 10px;
  border-left: 3px solid #124ea2; background: #f6f8fc; margin-bottom: 5px; }}
ol.trace li b {{ color: #124ea2; font-weight: 600; }}
ol.trace li em {{ color: #5c6778; font-style: normal; font-size: 12px; }}
</style></head><body>
<h1>规则卡 · 评测报告</h1>
<div class="cards">
<div class="card">页面<b>{data['n_files']}</b>含 {data['n_scored']} 条有标注</div>
<div class="card">只看种草<b>{data['keyword_accuracy']}</b></div>
<div class="card">只读首个数<b>{data['first_number_accuracy']}</b></div>
<div class="card">编译执行<b>{data['compiled_accuracy']}</b></div>
<div class="card">已核对官网<b>{data['verified_n']}</b></div>
</div>
<h2>错因分布</h2>{bars}
{_trace_block(data.get("trace_sample") or {})}
<h2>逐条结果</h2>
<table><tr><th>馆</th><th>切分</th><th>核对</th><th>标注</th><th>种草</th><th>首个数</th><th>编译</th><th>错因</th></tr>{table}</table>
<p class="note">{data['note']}</p>
</body></html>"""
    OUT.write_text(html, encoding="utf-8")
    print(f"已写出 {OUT}")


if __name__ == "__main__":
    main()
