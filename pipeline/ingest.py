from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ingest() -> dict:
    reviews = load_json(DATA / "sources" / "raw_reviews.json")
    by_source: dict[str, int] = {}
    for row in reviews:
        by_source[row["source"]] = by_source.get(row["source"], 0) + 1
    return {
        "step": "ingest",
        "tool": "pipeline.ingest",
        "records": reviews,
        "count": len(reviews),
        "by_source": by_source,
    }
