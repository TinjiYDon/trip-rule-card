"""打交稿 zip：源码 + 报告 + 说明，不含 .git 与缓存。"""

from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT.parent
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", ".idea", ".vscode"}
SKIP_NAMES = {".DS_Store", "Thumbs.db"}
SKIP_SUFFIX = {".pyc", ".pyo"}


def main() -> None:
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = OUT_DIR / f"规则卡-交稿包-{stamp}.zip"
    count = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIX:
                continue
            if path.name.startswith("_tmp"):
                continue
            rel = path.relative_to(ROOT)
            zf.write(path, arcname=str(Path("rule-card") / rel))
            count += 1
        readme = (
            "规则卡交稿包\n"
            "1. 解压后进入 rule-card\n"
            "2. 先读 docs/交稿说明.md\n"
            "3. python demo/server.py 打开 http://127.0.0.1:8765\n"
            "4. 评测报告 docs/report.html\n"
            f"打包文件数: {count}\n"
        )
        zf.writestr("请先读我.txt", readme)
    print(out)
    print(f"files={count}")


if __name__ == "__main__":
    main()
