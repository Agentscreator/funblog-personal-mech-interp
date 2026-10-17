#!/usr/bin/env python3
"""Render data/posts.json + data/scores.json into a static site in site/."""
import json
import shutil
from datetime import date
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
CONFIG = json.loads((ROOT / "config.json").read_text())

SECTIONS = {"research": "Research", "personal": "Personal"}
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
        p["engagement"] = s.get("engagement", 0)
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


def short_date(d):
    return date.fromisoformat(d).strftime("%b %Y")


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
<main>
<header>
  <a class="name" href="{rel}index.html">{escape(CONFIG["site_title"])}</a>
  <nav>{links}</nav>
</header>
{body}
</main>
</body>
</html>
"""


def entry(p, blurb=True):
    note = f'<p class="blurb">{escape(p["blurb"])}</p>' if blurb and p["blurb"] else ""
    return f"""<li>
  <a href="posts/{escape(p['slug'])}.html">{escape(p['title'])}</a>
  {note}
</li>"""


def dated(p):
    return f"""<li class="row">
  <a href="posts/{escape(p['slug'])}.html">{escape(p['title'])}</a>
  <time>{short_date(p['date'])}</time>
</li>"""


def build_index(posts):
    n = CONFIG.get("featured_per_section", 3)
    best = "".join(f"""<section id="{cat}">
  <h2>{label}</h2>
  <ul class="best">{"".join(entry(p) for p in ranked(posts, cat)[:n])}</ul>
</section>""" for cat, label in SECTIONS.items())
    # Without any likes/comments, trending is just date order and would duplicate "All writing".
    trending = ""
    if any(p["engagement"] for p in posts):
        hot = sorted(posts, key=lambda p: -p["trending"])[:CONFIG.get("trending_count", 4)]
        trending = f"""<section>
  <h2>Trending</h2>
  <ul class="list">{"".join(dated(p) for p in hot)}</ul>
</section>"""
    everything = sorted(posts, key=lambda p: p["date"], reverse=True)
    body = f"""<p class="intro">{escape(CONFIG["tagline"])}</p>
{best}
{trending}
<section>
  <h2>All writing</h2>
  <ul class="list">{"".join(dated(p) for p in everything)}</ul>
</section>"""
    return page(CONFIG["site_title"], body, description=CONFIG["tagline"])


def build_post(p, prev, nxt):
    sub = f'<p class="subtitle">{escape(p["subtitle"])}</p>' if p.get("subtitle") else ""
    origins = [(p["source"], p["url"])] + [(a["source"], a["url"]) for a in p.get("also_on", [])]
    orig = " and ".join(f'<a href="{escape(u)}">{SOURCE_NAMES[s]}</a>' for s, u in origins)
    nav = []
    if prev:
        nav.append(f'<a href="{escape(prev["slug"])}.html">← {escape(prev["title"])}</a>')
    if nxt:
        nav.append(f'<a class="next" href="{escape(nxt["slug"])}.html">{escape(nxt["title"])} →</a>')
    body = f"""<article>
  <h1>{escape(p['title'])}</h1>
  {sub}
  <p class="meta">{fmt_date(p['date'])}</p>
  <div class="prose">{p['html']}</div>
  <p class="meta">Originally published on {orig}.</p>
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
