from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from .ingest import DATA, load_json

CACHE = DATA / "llm_extract.json"


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def resolve_endpoint() -> dict | None:
    key = _env("LLM_API_KEY") or _env("OPENAI_API_KEY") or _env("GROQ_API_KEY")
    if not key:
        return None
    if _env("GROQ_API_KEY") and not _env("LLM_BASE_URL") and not _env("OPENAI_API_KEY"):
        base = "https://api.groq.com/openai/v1"
        model = _env("LLM_MODEL") or "llama-3.3-70b-versatile"
    else:
        base = _env("LLM_BASE_URL") or "https://api.openai.com/v1"
        model = _env("LLM_MODEL") or _env("OPENAI_MODEL") or "gpt-4o-mini"
    return {"key": key, "base": base.rstrip("/"), "model": model}


def _catalog() -> dict:
    clinics = load_json(DATA / "canonical_clinics.json")
    surgeons = load_json(DATA / "surgeons.json")
    procedures = load_json(DATA / "taxonomy.json")["procedures"]
    return {
        "clinic_ids": [c["id"] for c in clinics],
        "clinic_names": [
            {"id": c["id"], "en": c["name_en"], "ko": c["name_ko"], "aliases": c["aliases"]}
            for c in clinics
        ],
        "procedure_ids": [p["id"] for p in procedures],
        "surgeon_ids": [s["id"] for s in surgeons],
        "surgeons": [
            {"id": s["id"], "en": s["name_en"], "ko": s["name_ko"], "clinics": s["clinics"]}
            for s in surgeons
        ],
    }


def _system_prompt(catalog: dict) -> str:
    return (
        "You extract Gangnam clinic reviews for a medical-tourism index. "
        "Read Korean. Guess meaning. Return JSON only.\n"
        "For each review emit: id, clinic_id, procedure_id, surgeon_id, body_en, rating, rationale.\n"
        "clinic_id must be one of: "
        + ", ".join(catalog["clinic_ids"])
        + " or null if you cannot map it.\n"
        "procedure_id must be one of: "
        + ", ".join(catalog["procedure_ids"])
        + " or null.\n"
        "surgeon_id must be one of: "
        + ", ".join(catalog["surgeon_ids"])
        + " or null.\n"
        "body_en is English, no Hangul. rating is the patient's score as you understand it.\n"
        "Do not invent a clinic outside the list. If the name is unknown you may still pick the closest clinic — the solver will overrule you."
    )


def _chat(endpoint: dict, messages: list[dict]) -> str:
    payload = json.dumps(
        {
            "model": endpoint["model"],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": messages,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        endpoint["base"] + "/chat/completions",
        data=payload,
        headers={
            "Authorization": "Bearer " + endpoint["key"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def complete(reviews: list[dict]) -> dict:
    endpoint = resolve_endpoint()
    if endpoint is None:
        cached = json.loads(CACHE.read_text(encoding="utf-8"))
        return {**cached, "live": False}

    catalog = _catalog()
    out: dict[str, dict] = {}
    model = endpoint["model"]
    chunk = 8
    for i in range(0, len(reviews), chunk):
        batch = reviews[i : i + chunk]
        slim = [
            {
                "id": r["id"],
                "lang": r["lang"],
                "clinic_raw": r["clinic_raw"],
                "procedure_raw": r["procedure_raw"],
                "surgeon_raw": r.get("surgeon_raw"),
                "body": r["body"],
                "rating": r["rating"],
            }
            for r in batch
        ]
        raw = _chat(
            endpoint,
            [
                {"role": "system", "content": _system_prompt(catalog)},
                {
                    "role": "user",
                    "content": json.dumps({"reviews": slim}, ensure_ascii=False),
                },
            ],
        )
        parsed = json.loads(raw)
        rows = parsed.get("reviews", parsed if isinstance(parsed, list) else [parsed])
        for row in rows:
            if isinstance(row, dict) and row.get("id"):
                out[row["id"]] = row

    payload = {"model": model, "live": True, "records": out}
    CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
