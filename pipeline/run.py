from __future__ import annotations

import json
import sys
from pathlib import Path

from .constrain import constrain
from .extract import extract
from .ingest import ingest
from .publish import publish

ROOT = Path(__file__).resolve().parents[1]


def run_pipeline() -> dict:
    raw = ingest()
    extracted = extract(raw["records"])
    gated = constrain(extracted["records"])
    out = publish(raw, extracted, gated)
    summary = {
        "ingest": {"count": raw["count"], "by_source": raw["by_source"]},
        "extract": {"count": extracted["count"], "noisy": extracted["noisy"]},
        "constrain": gated["counts"] | {"reasons": gated["reasons"]},
        "publish": {"path": out["path"], "records": out["records"]},
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def main() -> int:
    run_pipeline()
    return 0


if __name__ == "__main__":
    sys.exit(main())
