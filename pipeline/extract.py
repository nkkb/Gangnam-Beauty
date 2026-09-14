from __future__ import annotations

import re
import unicodedata

from .llm import complete

HANGUL = re.compile(r"[\uac00-\ud7a3]")


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").casefold().strip()


def extract(raw_reviews: list[dict]) -> dict:
    llm = complete(raw_reviews)
    guesses = llm.get("records") or {}
    records = []
    noisy = 0
    for row in raw_reviews:
        g = guesses.get(row["id"]) or {}
        body_en = g.get("body_en") or row["body"]
        clinic_guess = g.get("clinic_id") or None
        procedure_guess = g.get("procedure_id") or None
        surgeon_guess = g.get("surgeon_id") or None
        leak = bool(HANGUL.search(body_en))
        record = {
            "id": row["id"],
            "source": row["source"],
            "lang": row["lang"],
            "date": row["date"],
            "rating": row["rating"],
            "clinic_raw": row["clinic_raw"],
            "clinic_guess": clinic_guess,
            "procedure_raw": row["procedure_raw"],
            "procedure_guess": procedure_guess,
            "surgeon_raw": row.get("surgeon_raw"),
            "surgeon_guess": surgeon_guess,
            "body_source": row["body"],
            "body_en": body_en,
            "has_photos": row["has_photos"],
            "has_receipt": row["has_receipt"],
            "price_krw": row.get("price_krw"),
            "script_leak": leak,
            "llm_rating": g.get("rating"),
            "llm_rationale": g.get("rationale"),
            "llm_model": llm.get("model"),
            "llm_live": bool(llm.get("live")),
        }
        if (
            clinic_guess is None
            or procedure_guess is None
            or leak
            or record["llm_rating"] != row["rating"]
        ):
            noisy += 1
        records.append(record)

    live = "live API" if llm.get("live") else "cached session pass"
    return {
        "step": "extract",
        "tool": f"pipeline.extract (LLM, {live})",
        "model": llm.get("model"),
        "live": bool(llm.get("live")),
        "records": records,
        "count": len(records),
        "noisy": noisy,
        "note": "LLM reads Korean and proposes clinic/procedure/surgeon plus English. Source rating, date, and price are not the model's to edit. The solver treats LLM ids as hints, never as facts.",
    }
