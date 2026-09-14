# Review Syndicate

Multi-step review desk for [Gangnam Beauty Guide](https://gangnambeautyguide.com).

Korean and English clinic reviews go in messy. A CP-SAT clinic assignment plus hard gates decide what a Western medical-tourism reader is allowed to see. The model (here a heuristic extract + glossary translate) is not trusted.

Live desk: https://gangnam.chronex-studio.com
Repo: https://github.com/nkkb/Gangnam-Beauty

This is fixture data. It is not a scrape of Naver, GangnamUnni, or any live clinic site.

## Pipeline

```
ingest → extract/translate → constrain (OR-Tools CP-SAT) → publish
```

1. **ingest** loads 49 reviews from five source files (`gangnamunni`, `naver_place`, `babitalk`, `realself`, `google_maps`). Hangul nicknames, English typos, event-package procedure names, future dates, junk ratings.
2. **extract** guesses clinic / procedure / surgeon and writes an English body. It is supposed to be sloppy. Nickname clinics (`팝플스`) are left unmatched on purpose. Two bodies keep Hangul so the next step has something to kill.
3. **constrain** is the product. OR-Tools assigns each raw clinic string to a canonical clinic or to unmatched. Then hard gates: rating ∈ {1, 1.5, …, 5}, procedure in taxonomy, surgeon rostered at that clinic, date ≤ pipeline day, KRW inside the procedure band, English body has no Hangul. Near-duplicates fold across sources.
4. **publish** writes `public/index.html` + `public/desk.json`.

Trust badges (`verified procedure`, `verified surgeon`) are set only after the solver accepts the row. That is the moat the application text talks about.

## Run

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pipeline.run
.venv/bin/pytest -q
```

Open `public/index.html`.

## Why CP, not another prompt

Extract will always over-match. `v-line` inside `diamond v-line hologram`. `han` inside `choi-hana`. Divergent translations of the same Korean story. A second LLM will agree with the first one. A constraint model will not.

## Cloudflare

Origin vhost is already up: `gangnam.chronex-studio.com` → `/var/www/gangnam-beauty`.

In the `chronex-studio.com` zone, add:

| Type | Name | IPv4 | Proxy | SSL |
| --- | --- | --- | --- | --- |
| A | gangnam | 185.182.185.141 | Proxied | Full |

Same pattern as `nayu` / `chass`. Full, not Full (strict) — origin cert is self-signed.
