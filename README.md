# Review Syndicate

Multi-step review desk for [Gangnam Beauty Guide](https://gangnambeautyguide.com).

Korean and English clinic reviews go in messy. A CP-SAT clinic assignment plus hard gates decide what a Western medical-tourism reader is allowed to see. The model (here a heuristic extract + glossary translate) is not trusted.

Live desk: https://chronex-studio.com/gangnam/
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

Origin is this box, same pattern as the other Chronex vhosts.

- Path that already works: `https://chronex-studio.com/gangnam/`
- Subdomain vhost is ready: `gangnam.chronex-studio.com` → `/var/www/gangnam-beauty`

In Cloudflare DNS for `chronex-studio.com`:

| Type | Name | Target | Proxy |
| --- | --- | --- | --- |
| CNAME | gangnam | chronex-studio.com | DNS only or proxied |

SSL mode Full is fine with the origin cert on the vhost. If you pointed a Gangnam Beauty Guide subdomain here instead, add that hostname to the same nginx server block.
