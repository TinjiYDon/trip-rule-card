"""读取标注同学维护的场馆 JSON。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENUE_DIR = ROOT / "data" / "venues"


def list_venues(split: str | None = None) -> list[dict]:
    venues = []
    for path in sorted(VENUE_DIR.glob("*.json")):
        venue = json.loads(path.read_text(encoding="utf-8"))
        venue["_file"] = path.name
        if split is None or venue.get("split") == split:
            venues.append(venue)
    return venues


def get_venue(venue_id: str) -> dict:
    for venue in list_venues():
        if venue["id"] == venue_id:
            return venue
    raise KeyError(venue_id)
