"""演示服务。演示同学只改 demo/。"""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from rulecard.load import get_venue, list_venues
from rulecard.pipeline import compile_and_run

DEMO_DIR = Path(__file__).resolve().parent
PORT = 8765


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._file(DEMO_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/api/venues":
            payload = [
                {
                    "id": venue["id"],
                    "name": venue["name"],
                    "city": venue["city"],
                    "split": venue["split"],
                    "verified": venue["verified"],
                    "source": venue.get("source") or "",
                    "promo_text": venue.get("promo_text") or "",
                    "page_text": venue.get("page_text") or "",
                }
                for venue in list_venues()
            ]
            self._json(payload)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/run":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        venue = get_venue(body["id"])
        if body.get("promo_text"):
            venue = {**venue, "promo_text": body["promo_text"]}
        result = compile_and_run(
            venue,
            int(body.get("age", 7)),
            float(body.get("height_m", 1.3)),
            body.get("benefits") or [],
        )
        self._json(result)

    def log_message(self, fmt: str, *args) -> None:
        return

    def _json(self, payload: object) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _file(self, path: Path, content_type: str) -> None:
        raw = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"规则卡演示 http://127.0.0.1:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
