from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def publish(ingest: dict, extract: dict, constrained: dict) -> dict:
    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "title": "Review Syndicate",
        "steps": [
            {
                "id": "ingest",
                "label": "Ingest",
                "tool": ingest["tool"],
                "out": f"{ingest['count']} raw reviews",
                "by_source": ingest["by_source"],
            },
            {
                "id": "extract",
                "label": "LLM extract",
                "tool": extract["tool"],
                "out": f"{extract['count']} structured rows, {extract['noisy']} left noisy",
                "note": extract["note"],
            },
            {
                "id": "constrain",
                "label": "Constrain",
                "tool": constrained["tool"],
                "out": (
                    f"{constrained['counts']['published']} published · "
                    f"{constrained['counts']['rejected']} rejected · "
                    f"{constrained['counts']['duplicates']} duplicates folded"
                ),
                "reasons": constrained["reasons"],
            },
            {
                "id": "publish",
                "label": "Publish",
                "tool": "pipeline.publish",
                "out": "static desk at public/index.html",
            },
        ],
        "counts": constrained["counts"],
        "reasons": constrained["reasons"],
        "assignment": constrained["assignment"],
        "reviews": constrained["accepted"],
        "rejected": constrained["rejected"],
        "duplicates": constrained["duplicates"],
    }

    public = ROOT / "public"
    public.mkdir(exist_ok=True)
    (public / "desk.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (public / "index.html").write_text(_html(), encoding="utf-8")
    (ROOT / "runs").mkdir(exist_ok=True)
    (ROOT / "runs" / "latest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return {
        "step": "publish",
        "tool": "pipeline.publish",
        "path": "public/index.html",
        "records": payload["counts"]["published"],
    }


def _html() -> str:
    return r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Review Syndicate — Gangnam Beauty Guide</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;1,500&family=IBM+Plex+Sans:wght@400;500;600&family=Noto+Serif+KR:wght@400;600&display=swap" rel="stylesheet" />
  <style>
    :root {
      --paper: #f3eee4;
      --ink: #1b1714;
      --muted: #6e6458;
      --rule: #d7cdc0;
      --wine: #7a2e32;
      --gold: #b0894f;
      --ok: #2c5d4a;
      --bad: #8a3030;
      --card: #fbf7ef;
    }
    * { box-sizing: border-box; }
    html, body { margin: 0; background: var(--paper); color: var(--ink); }
    body {
      font-family: "IBM Plex Sans", sans-serif;
      font-size: 15px;
      line-height: 1.5;
    }
    h1, h2, h3 { font-family: "Cormorant Garamond", serif; font-weight: 600; margin: 0; }
    a { color: var(--wine); }
    header {
      padding: 36px 28px 20px;
      border-bottom: 1px solid var(--ink);
      display: grid;
      gap: 8px;
      max-width: 1180px;
      margin: 0 auto;
    }
    .kicker {
      letter-spacing: 0.16em;
      text-transform: uppercase;
      font-size: 11px;
      color: var(--wine);
      font-weight: 600;
    }
    h1 { font-size: clamp(36px, 6vw, 64px); line-height: 0.95; }
    .lede { max-width: 62ch; color: var(--muted); }
    main { max-width: 1180px; margin: 0 auto; padding: 24px 28px 80px; }
    .stats {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1px;
      background: var(--ink);
      border: 1px solid var(--ink);
      margin: 28px 0;
    }
    .stats div { background: var(--card); padding: 16px 18px; }
    .stats b { display: block; font-family: "Cormorant Garamond", serif; font-size: 34px; }
    .stats span { color: var(--muted); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
    .steps { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 8px 0 32px; }
    .step {
      border-top: 2px solid var(--ink);
      padding-top: 10px;
    }
    .step em { font-style: italic; color: var(--gold); font-family: "Cormorant Garamond", serif; }
    .step p { color: var(--muted); font-size: 13px; margin: 8px 0 0; }
    .toolbar { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0 18px; }
    select, input[type="search"] {
      background: var(--card);
      border: 1px solid var(--rule);
      color: var(--ink);
      padding: 8px 10px;
      font: inherit;
    }
    .grid { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 28px; }
    article {
      background: var(--card);
      border: 1px solid var(--rule);
      padding: 16px 18px 14px;
      margin-bottom: 12px;
    }
    article h3 { font-size: 26px; }
    .meta { color: var(--muted); font-size: 12px; margin: 4px 0 10px; }
    .ko {
      font-family: "Noto Serif KR", serif;
      color: var(--muted);
      font-size: 13px;
      border-left: 2px solid var(--gold);
      padding-left: 10px;
      margin-top: 10px;
    }
    .badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
    .badges span {
      font-size: 10px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      border: 1px solid var(--ink);
      padding: 2px 7px;
    }
    .badges .ok { border-color: var(--ok); color: var(--ok); }
    .badges .no { border-color: var(--rule); color: var(--muted); }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); vertical-align: top; }
    th { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--muted); }
    .code { font-family: ui-monospace, monospace; font-size: 11px; color: var(--bad); }
    footer { margin-top: 40px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--rule); padding-top: 16px; }
    @media (max-width: 860px) {
      .stats, .steps, .grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <header>
    <div class="kicker">Gangnam Beauty Guide · take-home desk</div>
    <h1>Review Syndicate</h1>
    <p class="lede">
      An LLM reads the Korean. A CP-SAT clinic assignment plus hard gates decide
      what ships. The model is allowed to understand; it is not allowed to publish.
    </p>
  </header>
  <main>
    <div class="stats" id="stats"></div>
    <div class="steps" id="steps"></div>
    <div class="toolbar">
      <input id="q" type="search" placeholder="Search clinic, procedure, text" />
      <select id="clinic"><option value="">All clinics</option></select>
      <select id="proc"><option value="">All procedures</option></select>
      <select id="src"><option value="">All sources</option></select>
    </div>
    <div class="grid">
      <section>
        <h2>Published English reviews</h2>
        <div id="reviews"></div>
      </section>
      <section>
        <h2>Quarantine</h2>
        <p class="lede" style="margin:8px 0 12px">The model understood these. The solver still said no.</p>
        <table>
          <thead><tr><th>id</th><th>code</th><th>why</th></tr></thead>
          <tbody id="rej"></tbody>
        </table>
        <h2 style="margin-top:28px">Duplicates folded</h2>
        <table>
          <thead><tr><th>id</th><th>kept</th><th>source</th></tr></thead>
          <tbody id="dup"></tbody>
        </table>
      </section>
    </div>
    <footer>
      Fixture corpus, not a live scrape of Naver / GangnamUnni. Pipeline:
      <code>python -m pipeline.run</code>
      · source
      <a href="https://github.com/nkkb/Gangnam-Beauty">github.com/nkkb/Gangnam-Beauty</a>
    </footer>
  </main>
  <script>
    const stars = (n) => "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));
    fetch("./desk.json").then(r => r.json()).then(data => {
      const c = data.counts;
      document.getElementById("stats").innerHTML = [
        ["Ingested", c.in],
        ["Rejected", c.rejected],
        ["Duplicates", c.duplicates],
        ["Published", c.published],
      ].map(([k,v]) => `<div><b>${v}</b><span>${k}</span></div>`).join("");
      document.getElementById("steps").innerHTML = data.steps.map((s,i) =>
        `<div class="step"><em>0${i+1}</em><h3>${s.label}</h3><p>${s.tool}<br>${s.out}</p></div>`
      ).join("");
      const clinics = [...new Set(data.reviews.map(r => r.clinic_en))].sort();
      const procs = [...new Set(data.reviews.map(r => r.procedure_id))].sort();
      const srcs = [...new Set(data.reviews.map(r => r.source))].sort();
      const fill = (id, items) => {
        const el = document.getElementById(id);
        items.forEach(v => { const o = document.createElement("option"); o.value = v; o.textContent = v; el.appendChild(o); });
      };
      fill("clinic", clinics); fill("proc", procs); fill("src", srcs);
      const box = document.getElementById("reviews");
      const draw = () => {
        const q = document.getElementById("q").value.toLowerCase();
        const clinic = document.getElementById("clinic").value;
        const proc = document.getElementById("proc").value;
        const src = document.getElementById("src").value;
        const rows = data.reviews.filter(r => {
          if (clinic && r.clinic_en !== clinic) return false;
          if (proc && r.procedure_id !== proc) return false;
          if (src && r.source !== src) return false;
          const hay = (r.body_en + r.clinic_en + r.procedure_id + r.clinic_raw).toLowerCase();
          return !q || hay.includes(q);
        });
        box.innerHTML = rows.map(r => `
          <article>
            <div class="kicker">${r.source} · ${r.date}</div>
            <h3>${r.clinic_en}</h3>
            <div class="meta">${stars(r.rating)} ${r.rating} · ${r.procedure_id.replace("-", " ")}${r.surgeon_id ? " · " + r.surgeon_id : ""}${r.also_seen_on.length ? " · also " + r.also_seen_on.join(", ") : ""}</div>
            <p>${r.body_en}</p>
            <div class="ko">${r.body_source}</div>
            <div class="badges">
              <span class="${r.verified_procedure ? "ok" : "no"}">${r.verified_procedure ? "verified procedure" : "unverified procedure"}</span>
              <span class="${r.verified_surgeon ? "ok" : "no"}">${r.verified_surgeon ? "verified surgeon" : "unverified surgeon"}</span>
              ${r.llm_procedure_disagreed ? `<span class="no">solver overrode procedure (${r.procedure_guess} → ${r.procedure_id})</span>` : `<span class="no">model ${r.procedure_guess || "—"} → solver ${r.procedure_id}</span>`}
              ${r.llm_clinic_disagreed ? `<span class="no">solver overrode clinic</span>` : ""}
              ${r.price_krw ? `<span class="no">${r.price_krw.toLocaleString()} KRW</span>` : ""}
            </div>
          </article>`).join("") || "<p>No reviews match.</p>";
      };
      ["q","clinic","proc","src"].forEach(id => document.getElementById(id).addEventListener("input", draw));
      draw();
      document.getElementById("rej").innerHTML = data.rejected.map(r =>
        `<tr><td>${r.id}</td><td class="code">${r.reject_code}</td><td>${r.reject_detail}</td></tr>`
      ).join("");
      document.getElementById("dup").innerHTML = data.duplicates.map(r =>
        `<tr><td>${r.id}</td><td>${r.duplicate_of}</td><td>${r.source}</td></tr>`
      ).join("");
    });
  </script>
</body>
</html>
"""
