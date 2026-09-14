from pipeline.constrain import alias_cost, constrain
from pipeline.extract import extract
from pipeline.ingest import ingest, load_json, DATA


def test_typo_id_hospital_assigns():
    clinics = load_json(DATA / "canonical_clinics.json")
    idh = next(c for c in clinics if c["id"] == "id-hospital")
    assert alias_cost("ID Hosptial", idh) is not None
    assert alias_cost("ID Hosptial", idh) <= 12


def test_unknown_clinic_unmatched():
    clinics = load_json(DATA / "canonical_clinics.json")
    costs = [alias_cost("로얄크라운드림라인의원", c) for c in clinics]
    assert all(c is None or c > 20 for c in costs)


def test_llm_understands_and_solver_still_gates():
    raw = ingest()["records"]
    extracted = {r["id"]: r for r in extract(raw)["records"]}
    gated = constrain(list(extracted.values()))
    codes = {r["id"]: r["reject_code"] for r in gated["rejected"]}
    published = {r["id"]: r for r in gated["accepted"]}
    dup_of = {r["id"]: r["duplicate_of"] for r in gated["duplicates"]}

    assert extracted["junk-proc-1"]["procedure_guess"] == "facial-contouring"
    assert codes["junk-proc-1"] == "PROCEDURE_TAXONOMY"

    assert extracted["junk-proc-2"]["procedure_guess"] == "skin-booster"
    assert codes["junk-proc-2"] == "PROCEDURE_TAXONOMY"

    assert extracted["unknown-clinic"]["clinic_guess"] == "id-hospital"
    assert codes["unknown-clinic"] == "CLINIC_UNMATCHED"

    assert extracted["bad-rating-1"]["llm_rating"] == 5.0
    assert extracted["bad-rating-1"]["rating"] == 6
    assert codes["bad-rating-1"] == "RATING_RANGE"

    assert extracted["gm-003"]["surgeon_guess"] == "han-yuri"
    assert published["gm-003"]["surgeon_id"] == "han-yuri"

    assert codes["future-1"] == "DATE_FUTURE"
    assert codes["mismatch-surgeon"] == "SURGEON_AFFILIATION"
    assert codes["price-high"] == "PRICE_BAND"
    assert "gu-001" in published
    assert dup_of["np-001"] == "gu-001"
    assert published["np-004"]["procedure_id"] == "rhinoplasty"
    assert extracted["gu-014"]["procedure_guess"] == "revision-rhinoplasty"
    assert published["gu-014"]["procedure_id"] == "rhinoplasty"
    assert published["gu-014"]["llm_procedure_disagreed"] is True
