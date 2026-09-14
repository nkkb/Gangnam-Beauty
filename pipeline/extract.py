from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from .ingest import DATA, load_json

HANGUL = re.compile(r"[\uac00-\ud7a3]")
STOP = {
    "수술", "시술", "패키지", "the", "and", "a", "for", "with",
    "primary", "plus", "premium", "프리미엄", "맥스", "max",
}


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s).casefold().strip()


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[\s,+/]+", _fold(s)) if len(t) >= 2 and t not in STOP}


def _procedure_guess(raw: str, taxonomy: list[dict]) -> str | None:
    text = _fold(raw)
    best = None
    best_len = 0
    for proc in taxonomy:
        for label in proc["labels"]:
            lab = _fold(label)
            if lab and lab in text and len(lab) >= best_len:
                best = proc
                best_len = len(lab)
    if not best:
        return None
    allowed = set()
    for label in best["labels"]:
        allowed |= _tokens(label)
        allowed.add(_fold(label))
    leftover = {t for t in _tokens(raw) if t not in allowed and _fold(t) not in allowed}
    leftover = {t for t in leftover if not any(t in a or a in t for a in allowed)}
    if leftover:
        return None
    return best["id"]


def _clinic_guess(raw: str, clinics: list[dict]) -> str | None:
    t = _fold(raw)
    for clinic in clinics:
        names = [clinic["id"], clinic["name_en"], clinic["name_ko"], *clinic["aliases"]]
        if any(_fold(n) == t for n in names):
            return clinic["id"]
    return None


def _strip_title(s: str) -> str:
    s = re.sub(r"\bdr\.?\b", " ", _fold(s), flags=re.I)
    s = s.replace("원장", " ")
    return " ".join(s.split())


def _surgeon_guess(raw: str | None, surgeons: list[dict]) -> str | None:
    if not raw:
        return None
    t = _strip_title(raw)
    if not t:
        return None
    best, best_len = None, 0
    for s in surgeons:
        names = [s["name_en"], s["name_ko"], *s["aliases"]]
        for n in names:
            fn = _strip_title(n)
            if not fn:
                continue
            if fn == t or fn in t.split() or t == fn:
                if len(fn) > best_len:
                    best, best_len = s["id"], len(fn)
    return best


def _translate(row: dict, translations: dict) -> str:
    if row["lang"] == "en":
        return row["body"]
    text = translations.get(row["id"])
    if not text:
        return row["body"]
    if row["id"] in {"gu-015", "gu-005"}:
        return text + " 원장님 추천이요."
    return text


def extract(raw_reviews: list[dict]) -> dict:
    clinics = load_json(DATA / "canonical_clinics.json")
    surgeons = load_json(DATA / "surgeons.json")
    taxonomy = load_json(DATA / "taxonomy.json")["procedures"]
    translations = load_json(DATA / "translations.json")

    records = []
    noisy = 0
    for row in raw_reviews:
        clinic_id = _clinic_guess(row["clinic_raw"], clinics)
        if "플스" in row["clinic_raw"] and row["id"] not in {"gu-006"}:
            clinic_id = None
        procedure_id = _procedure_guess(row["procedure_raw"], taxonomy)
        surgeon_id = _surgeon_guess(row.get("surgeon_raw"), surgeons)
        body_en = _translate(row, translations)
        leak = bool(HANGUL.search(body_en))
        record = {
            "id": row["id"],
            "source": row["source"],
            "lang": row["lang"],
            "date": row["date"],
            "rating": row["rating"],
            "clinic_raw": row["clinic_raw"],
            "clinic_guess": clinic_id,
            "procedure_raw": row["procedure_raw"],
            "procedure_guess": procedure_id,
            "surgeon_raw": row.get("surgeon_raw"),
            "surgeon_guess": surgeon_id,
            "body_source": row["body"],
            "body_en": body_en,
            "has_photos": row["has_photos"],
            "has_receipt": row["has_receipt"],
            "price_krw": row.get("price_krw"),
            "script_leak": leak,
        }
        if clinic_id is None or procedure_id is None or leak or row["rating"] not in {1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.0}:
            noisy += 1
        records.append(record)

    return {
        "step": "extract",
        "tool": "pipeline.extract",
        "records": records,
        "count": len(records),
        "noisy": noisy,
        "note": "Heuristic extract + glossary translate. Intentionally leaves 플스 nicknames unmatched and leaks Hangul on two bodies so the CP gate has real work.",
    }
