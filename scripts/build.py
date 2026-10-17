#!/usr/bin/env python3
"""Render data/posts.json + data/rankings.json into a static site in site/."""
import json
import shutil
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
CONFIG = json.loads((ROOT / "config.json").read_text())

SECTIONS = {
    "research": ("Best Research", "AI safety, evaluation, decision-making and incentives."),
    "personal": ("Best Personal", "Short stories, poems and essays that have nothing to do with work."),
}
SOURCE_NAMES = {"substack": "Substack", "lesswrong": "LessWrong"}


def load():
    posts = json.loads((ROOT / "data" / "posts.json").read_text())
    scores = json.loads((ROOT / "data" / "scores.json").read_text())
    overrides = json.loads((ROOT / "data" / "overrides.json").read_text()).get("posts", {})
    out = []
    for p in posts:
        s = scores[p["id"]]
        o = overrides.get(p["slug"], {})
        if o.get("hide"):
            continue
        p["category"] = o.get("category") or s["category"]
        p["score"] = s["best"] + o.get("boost", 0)
        p["trending"] = s["trending"]
        p["provisional"] = s["quality_source"] == "provisional"
        p["pin"] = bool(o.get("pin"))
        p["blurb"] = o.get("blurb") or s["blurb"] or p.get("subtitle") or ""
        out.append(p)
    return out


def ranked(posts, cat):
    pool = [p for p in posts if p["category"] == cat]
    return sorted(pool, key=lambda p: (not p["pin"], -p["score"], p["date"]))


def fmt_date(d):
    return date.fromisoformat(d).strftime("%b %-d, %Y")


def read_time(words):
    return f"{max(1, round(words / 230))} min read"


def page(title, body, *, description="", canonical="", depth=0):
    rel = "../" * depth
    canon = f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ""
    links = " ".join(f'<a href="{escape(u)}" rel="me noopener">{escape(n)}</a>' for n, u in CONFIG["links"].items())
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
{canon}
<link rel="stylesheet" href="{rel}style.css">
</head>
<body>
<header class="masthead"><div class="wrap">
  <a class="name" href="{rel}index.html">{escape(CONFIG["site_title"])}</a>
  <nav>{links}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="wrap"><p>Pulled automatically from LessWrong and Substack. Picks chosen by having Claude read the whole corpus.</p></footer>
</body>
</html>
"""


def card(p, rank=None):
    num = f'<span class="rank">{rank:02d}</span>' if rank else ""
    new = '<span class="badge">New</span>' if p["provisional"] else ""
    return f"""<article class="card">
  {num}
  <div>
    <h3><a href="posts/{escape(p['slug'])}.html">{escape(p['title'])}</a>{new}</h3>
    <p class="blurb">{escape(p['blurb'])}</p>
    <p class="meta">{fmt_date(p['date'])} · {read_time(p['words'])} · {SOURCE_NAMES[p['source']]}</p>
  </div>
</article>"""


def row(p):
    return f"""<li><a href="posts/{escape(p['slug'])}.html">{escape(p['title'])}</a>
  <span class="meta">{fmt_date(p['date'])}</span></li>"""


def build_index(posts):
    n = CONFIG.get("featured_per_section", 3)
    featured = []
    archive = []
    for cat, (label, desc) in SECTIONS.items():
        picks = ranked(posts, cat)[:n]
        featured.append(f"""<section class="shelf" id="{cat}">
  <h2>{label}</h2>
  <p class="shelf-desc">{desc}</p>
  {"".join(card(p, i + 1) for i, p in enumerate(picks))}
</section>""")
        by_date = sorted((p for p in posts if p["category"] == cat), key=lambda p: p["date"], reverse=True)
        archive.append(f"""<section>
  <h3>All {cat} · {len(by_date)}</h3>
  <ul class="archive">{"".join(row(p) for p in by_date)}</ul>
</section>""")
    hot = sorted(posts, key=lambda p: -p["trending"])[:CONFIG.get("trending_count", 4)]
    trend = "".join(f"""<a class="chip" href="posts/{escape(p['slug'])}.html">
  <span class="chip-cat">{p['category']}</span>{escape(p['title'])}</a>""" for p in hot)
    body = f"""<p class="tagline">{escape(CONFIG["tagline"])}</p>
<section class="trending"><h2>New &amp; trending</h2><div class="chips">{trend}</div></section>
<div class="shelves">{"".join(featured)}</div>
<h2 class="archive-title">Everything</h2>
<div class="shelves">{"".join(archive)}</div>"""
    return page(CONFIG["site_title"], body, description=CONFIG["tagline"])


def build_post(p, prev, nxt):
    sub = f'<p class="subtitle">{escape(p["subtitle"])}</p>' if p.get("subtitle") else ""
    origins = [(p["source"], p["url"])] + [(a["source"], a["url"]) for a in p.get("also_on", [])]
    orig = " · ".join(f'<a href="{escape(u)}">{SOURCE_NAMES[s]}</a>' for s, u in origins)
    nav = []
    if prev:
        nav.append(f'<a href="{escape(prev["slug"])}.html">← {escape(prev["title"])}</a>')
    if nxt:
        nav.append(f'<a class="next" href="{escape(nxt["slug"])}.html">{escape(nxt["title"])} →</a>')
    body = f"""<article class="post">
  <p class="kicker"><a href="../index.html#{p['category']}">{SECTIONS[p['category']][0]}</a></p>
  <h1>{escape(p['title'])}</h1>
  {sub}
  <p class="meta">{fmt_date(p['date'])} · {read_time(p['words'])} · Originally on {orig}</p>
  <div class="prose">{p['html']}</div>
  <p class="discuss">Comment or subscribe on {orig}.</p>
</article>
<nav class="pager">{"".join(nav)}</nav>"""
    return page(f"{p['title']} · {CONFIG['site_title']}", body,
                description=p["blurb"], canonical=p["url"], depth=1)


def main():
    posts = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "style.css", OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
    (OUT / "index.html").write_text(build_index(posts))
    for cat in SECTIONS:
        seq = ranked(posts, cat)
        for i, p in enumerate(seq):
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            (OUT / "posts" / f"{p['slug']}.html").write_text(build_post(p, prev, nxt))
    print(f"built {len(posts)} posts -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
