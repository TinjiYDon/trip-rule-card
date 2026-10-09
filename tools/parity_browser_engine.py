"""用 Node 跑浏览器引擎，与 Python compile_and_run 对拍。"""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main() -> None:
    from rulecard.load import list_venues
    from rulecard.pipeline import compile_and_run

    engine = (ROOT / "demo" / "rulecard_browser.js").read_text(encoding="utf-8")
    venues = list_venues()
    payload = []
    for venue in venues:
        gold = venue.get("gold") or {}
        age = gold.get("age", 7)
        height = gold.get("height_m", 1.3)
        py = compile_and_run(venue, age, height)
        payload.append(
            {
                "venue": {
                    "id": venue["id"],
                    "page_text": venue.get("page_text") or "",
                    "promo_text": venue.get("promo_text") or "",
                    "gold": venue.get("gold"),
                },
                "age": age,
                "height_m": height,
                "py": py["compiled"]["ticket"],
            }
        )
    script = (
        engine
        + "\nconst rows = "
        + json.dumps(payload, ensure_ascii=False)
        + ";\n"
        + "const out = rows.map(r => {\n"
        + "  const js = RuleCardBrowser.compileAndRun(r.venue, r.age, r.height_m).compiled.ticket;\n"
        + "  return {id: r.venue.id, py: r.py, js, ok: js === r.py};\n"
        + "});\n"
        + "console.log(JSON.stringify(out));\n"
    )
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".js", delete=False) as fh:
        fh.write(script)
        path = fh.name
    raw = subprocess.check_output(["node", path], text=True, encoding="utf-8")
    rows = json.loads(raw)
    bad = [row for row in rows if not row["ok"]]
    print(json.dumps({"n": len(rows), "mismatch": bad}, ensure_ascii=False, indent=2))
    if bad:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
