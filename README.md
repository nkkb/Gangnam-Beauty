# Review Syndicate

LLM + CP-SAT desk for [Gangnam Beauty Guide](https://gangnambeautyguide.com).

The model reads Korean reviews and proposes clinic / procedure / surgeon plus an English body. That is the nondeterministic half — nicknames, marketing procedure names, “Dr. Han”, translation.

The solver is the other half. OR-Tools assigns clinic identity from aliases (the LLM can only cheapen a feasible match, never create one). Hard gates then check taxonomy evidence on the raw string, surgeon roster, source rating, source date, price band, and Hangul leaking into English. Source rating/date/price are not the model’s to edit. Trust badges are set only after the solver accepts the row.

Live desk: https://gangnam.chronex-studio.com
Repo: https://github.com/nkkb/Gangnam-Beauty

Fixture corpus. Not a scrape of Naver or GangnamUnni.

## Pipeline

```
ingest → LLM extract/translate → CP-SAT + hard gates → publish
```

The interesting disagreements:

- Model maps `diamond v-line hologram` → `facial-contouring`. Solver rejects `PROCEDURE_TAXONOMY` because leftover tokens are not in the procedure map.
- Model maps an unknown 상호 to ID Hospital. Solver rejects `CLINIC_UNMATCHED`. The LLM cannot invent a clinic.
- Model clamps a UI `6` star to `5`. Solver still reads the source `6` and rejects `RATING_RANGE`.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pipeline.seed_llm   # writes data/llm_extract.json
.venv/bin/python -m pipeline.run
.venv/bin/pytest -q
```

Live model (optional): copy `.env.example`, set `OPENAI_API_KEY` or `GROQ_API_KEY`, run `python -m pipeline.run`. That overwrites the cache.

## Cloudflare

Origin vhost is already up: `gangnam.chronex-studio.com` → `/var/www/gangnam-beauty`.

| Type | Name | IPv4 | Proxy | SSL |
| --- | --- | --- | --- | --- |
| A | gangnam | 185.182.185.141 | Proxied | Full |
