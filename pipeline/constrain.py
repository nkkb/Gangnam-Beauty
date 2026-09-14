from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from pathlib import Path

from ortools.sat.python import cp_model

from .ingest import DATA, load_json

TODAY = date(2026, 9, 14)
UNMATCHED_COST = 80
MAX_MATCH_COST = 28
ALLOWED_SOURCES = {"gangnamunni", "naver_place", "babitalk", "realself", "google_maps"}
ALLOWED_RATINGS = {10, 15, 20, 25, 30, 35, 40, 45, 50}
HANGUL = re.compile(r"[\uac00-\ud7a3]")


def _fold(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "").casefold().strip()


STOP = {
    "수술", "시술", "패키지", "the", "and", "a", "for", "with",
    "primary", "plus", "premium", "프리미엄", "맥스", "max",
}


def _word_tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[\s,+/]+", _fold(s)) if len(t) >= 2 and t not in STOP}


def _tokens(s: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9가-힣]+", _fold(s)) if len(t) >= 2}


def procedure_supported(raw: str, proc_id: str | None, taxonomy: dict) -> bool:
    proc = taxonomy.get(proc_id or "")
    if not proc:
        return False
    text = _fold(raw)
    labels = proc["labels"]
    if not any(_fold(lab) in text for lab in labels if _fold(lab)):
        return False
    allowed: set[str] = set()
    for lab in labels:
        allowed |= _word_tokens(lab)
        allowed.add(_fold(lab))
    leftover = {
        t
        for t in _word_tokens(raw)
        if t not in allowed and not any(t in a or a in t for a in allowed)
    }
    return not leftover


def _resolve_procedure(raw: str, llm_id: str | None, taxonomy: dict) -> tuple[str | None, bool]:
    if procedure_supported(raw, llm_id, taxonomy):
        return llm_id, False
    text = _fold(raw)
    best_id, best_len = None, 0
    for pid, proc in taxonomy.items():
        if not procedure_supported(raw, pid, taxonomy):
            continue
        for lab in proc["labels"]:
            fl = _fold(lab)
            if fl and fl in text and len(fl) >= best_len:
                best_id, best_len = pid, len(fl)
    return best_id, True


def levenshtein(a: str, b: str) -> int:
    a, b = _fold(a), _fold(b)
    if a == b:
        return 0
    if not a or not b:
        return max(len(a), len(b))
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def alias_cost(raw: str, clinic: dict) -> int | None:
    names = [clinic["id"], clinic["name_en"], clinic["name_ko"], *clinic["aliases"]]
    t = _fold(raw)
    if any(_fold(n) == t for n in names):
        return 0
    if any(_fold(n) in t or t in _fold(n) for n in names if len(_fold(n)) >= 2):
        return 6
    raw_tok, best = _tokens(raw), None
    for n in names:
        other = _tokens(n)
        if not raw_tok or not other:
            continue
        j = len(raw_tok & other) / len(raw_tok | other)
        dist = levenshtein(raw, n)
        cost = int(round((1 - j) * 24 + dist * 4))
        if best is None or cost < best:
            best = cost
    if best is None:
        return None
    return best if best <= MAX_MATCH_COST else None


def _rating_x10(value) -> int | None:
    try:
        x = int(round(float(value) * 10))
    except (TypeError, ValueError):
        return None
    return x


def _grams(text: str) -> set[str]:
    s = re.sub(r"[^a-z0-9가-힣]+", "", _fold(text))
    if len(s) < 4:
        return {s} if s else set()
    return {s[i : i + 3] for i in range(len(s) - 2)}


def _jaccard(a: str, b: str) -> float:
    ga, gb = _grams(a), _grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def assign_clinics(records: list[dict], clinics: list[dict]) -> dict[str, str | None]:
    names = [r["clinic_raw"] for r in records]
    unique = list(dict.fromkeys(names))
    llm_by_raw: dict[str, str] = {}
    for r in records:
        guess = r.get("clinic_guess")
        if guess and r["clinic_raw"] not in llm_by_raw:
            llm_by_raw[r["clinic_raw"]] = guess
    model = cp_model.CpModel()
    m = len(clinics)
    x = []
    unmatched = []
    objective = []
    for i, raw in enumerate(unique):
        row = [model.NewBoolVar(f"x_{i}_{j}") for j in range(m)]
        u = model.NewBoolVar(f"u_{i}")
        x.append(row)
        unmatched.append(u)
        model.Add(sum(row) + u == 1)
        for j, clinic in enumerate(clinics):
            cost = alias_cost(raw, clinic)
            if cost is None:
                model.Add(row[j] == 0)
                continue
            if llm_by_raw.get(raw) == clinic["id"]:
                cost = max(0, cost - 8)
            objective.append(row[j] * cost)
        objective.append(u * UNMATCHED_COST)
    model.Minimize(sum(objective))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 5.0
    status = solver.Solve(model)
    mapping: dict[str, str | None] = {}
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for raw in unique:
            mapping[raw] = None
        return mapping
    for i, raw in enumerate(unique):
        if solver.Value(unmatched[i]):
            mapping[raw] = None
            continue
        mapping[raw] = next(
            clinics[j]["id"] for j in range(m) if solver.Value(x[i][j])
        )
    return mapping


def constrain(extracted: list[dict]) -> dict:
    clinics = load_json(DATA / "canonical_clinics.json")
    surgeons = {s["id"]: s for s in load_json(DATA / "surgeons.json")}
    taxonomy = {p["id"]: p for p in load_json(DATA / "taxonomy.json")["procedures"]}
    clinic_by_id = {c["id"]: c for c in clinics}

    assignment = assign_clinics(extracted, clinics)

    accepted: list[dict] = []
    rejected: list[dict] = []
    reasons: dict[str, int] = {}

    def reject(row: dict, code: str, detail: str) -> None:
        reasons[code] = reasons.get(code, 0) + 1
        rejected.append({**row, "reject_code": code, "reject_detail": detail})

    for row in extracted:
        clinic_id = assignment.get(row["clinic_raw"])
        if not clinic_id:
            guessed = row.get("clinic_guess")
            extra = f"; model said {guessed}" if guessed else ""
            reject(row, "CLINIC_UNMATCHED", f"no canonical match for {row['clinic_raw']!r}{extra}")
            continue

        rating = _rating_x10(row["rating"])
        if rating not in ALLOWED_RATINGS:
            reject(row, "RATING_RANGE", f"rating {row['rating']} is not in 1–5 half-stars")
            continue

        if row["source"] not in ALLOWED_SOURCES:
            reject(row, "SOURCE_UNKNOWN", row["source"])
            continue

        try:
            posted = date.fromisoformat(row["date"])
        except ValueError:
            reject(row, "DATE_FUTURE", f"unreadable date {row['date']}")
            continue
        if posted > TODAY:
            reject(row, "DATE_FUTURE", f"{row['date']} is after pipeline day {TODAY.isoformat()}")
            continue

        proc, proc_overridden = _resolve_procedure(
            row.get("procedure_raw") or "", row.get("procedure_guess"), taxonomy
        )
        if not proc:
            reject(
                row,
                "PROCEDURE_TAXONOMY",
                f"model said {row.get('procedure_guess')!r} for {row['procedure_raw']!r}; raw text does not support a taxonomy id",
            )
            continue

        if HANGUL.search(row.get("body_en") or ""):
            reject(row, "TRANSLATION_SCRIPT", "English body still contains Hangul")
            continue

        sid = row.get("surgeon_guess")
        if sid:
            aff = surgeons.get(sid)
            if not aff or clinic_id not in aff["clinics"]:
                reject(
                    row,
                    "SURGEON_AFFILIATION",
                    f"{sid} is not rostered at {clinic_id}",
                )
                continue

        price = row.get("price_krw")
        if isinstance(price, int):
            lo, hi = taxonomy[proc]["band_krw"]
            if price < lo * 0.4 or price > hi * 1.6:
                reject(row, "PRICE_BAND", f"{price} KRW outside {proc} band {lo}–{hi}")
                continue

        clinic = clinic_by_id[clinic_id]
        llm_clinic = row.get("clinic_guess")
        verified_procedure = bool(row["has_photos"] or row["has_receipt"])
        verified_surgeon = bool(sid) and clinic_id in surgeons.get(sid, {}).get("clinics", [])
        accepted.append(
            {
                **row,
                "clinic_id": clinic_id,
                "clinic_en": clinic["name_en"],
                "clinic_ko": clinic["name_ko"],
                "district": clinic["district"],
                "procedure_id": proc,
                "surgeon_id": sid,
                "verified_procedure": verified_procedure,
                "verified_surgeon": verified_surgeon,
                "llm_clinic_disagreed": bool(llm_clinic) and llm_clinic != clinic_id,
                "llm_procedure_disagreed": proc_overridden and row.get("procedure_guess") != proc,
                "trust_score": int(verified_procedure) + int(verified_surgeon) + (2 if row["has_receipt"] else 0),
            }
        )

    published, duplicates = _dedupe(accepted)
    reasons["DUPLICATE_DROPPED"] = len(duplicates)

    return {
        "step": "constrain",
        "tool": "pipeline.constrain (OR-Tools CP-SAT)",
        "assignment": assignment,
        "accepted": published,
        "rejected": rejected,
        "duplicates": duplicates,
        "reasons": reasons,
        "counts": {
            "in": len(extracted),
            "rejected": len(rejected),
            "duplicates": len(duplicates),
            "published": len(published),
        },
    }


def _near_dup(a: dict, b: dict) -> bool:
    if a["clinic_id"] != b["clinic_id"]:
        return False
    if _jaccard(a["body_en"], b["body_en"]) >= 0.58:
        return True
    if _jaccard(a["body_source"], b["body_source"]) >= 0.4:
        return True
    same_proc = a.get("procedure_id") == b.get("procedure_id")
    same_price = bool(a.get("price_krw")) and a.get("price_krw") == b.get("price_krw")
    da = date.fromisoformat(a["date"])
    db = date.fromisoformat(b["date"])
    return same_proc and same_price and abs((da - db).days) <= 4


def _dedupe(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    keep: list[dict] = []
    dropped: list[dict] = []
    for row in sorted(rows, key=lambda r: (r["date"], r["id"])):
        twin = next((seen for seen in keep if _near_dup(seen, row)), None)
        if twin:
            twin.setdefault("also_seen_on", [])
            if row["source"] not in twin["also_seen_on"] and row["source"] != twin["source"]:
                twin["also_seen_on"].append(row["source"])
            dropped.append({**row, "duplicate_of": twin["id"]})
            continue
        keep.append({**row, "also_seen_on": []})
    return keep, dropped


def fingerprint(text: str) -> str:
    return hashlib.sha1(_fold(text).encode("utf-8")).hexdigest()[:12]
