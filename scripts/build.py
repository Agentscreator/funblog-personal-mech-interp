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

SECTIONS = {"personal": "Personal", "research": "Research"}
# (key, nav label, file, one-line explainer). The first page is the landing page.
PAGES = [("trending", "Trending", "index.html", "What people are reading right now."),
         ("personal", "Personal", "personal.html", "Stories, poems and essays, best first."),
         ("research", "Research", "research.html", "AI safety and evaluation, best first.")]
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


def page(title, body, *, description="", canonical="", depth=0, current=""):
    rel = "../" * depth
    canon = f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ""
    here = ' aria-current="page"'
    tabs = " ".join(f'<a href="{rel}{href}"{here if key == current else ""}>{label}</a>'
                    for key, label, href, _ in PAGES)
    email = escape(CONFIG["email"])
    links = " · ".join([f'<a href="mailto:{email}">{email}</a>'] + [
        f'<a href="{escape(u)}" rel="me noopener">{escape(n)}</a>' for n, u in CONFIG["links"].items()])
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
  <p class="links">{links}</p>
  <nav class="tabs">{tabs}</nav>
</header>
{body}
</main>
</body>
</html>
"""


def entry(p):
    note = f'<span class="blurb">{escape(p["blurb"])}</span>' if p["blurb"] else ""
    return f"""<li><a class="item" href="posts/{escape(p['slug'])}.html">
  <span class="row"><span class="title">{escape(p['title'])}</span><time>{short_date(p['date'])}</time></span>
  {note}
</a></li>"""


def listing(key, posts):
    label, intro = next((l, i) for k, l, _, i in PAGES if k == key)
    body = f"""<p class="intro">{escape(intro)}</p>
<ul class="list">{"".join(entry(p) for p in posts)}</ul>"""
    title = CONFIG["site_title"] if key == PAGES[0][0] else f"{label} · {CONFIG['site_title']}"
    return page(title, body, description=CONFIG["tagline"], current=key)


def build_pages(posts):
    # Without any likes/comments, trending is just date order.
    if any(p["engagement"] for p in posts):
        hot = sorted(posts, key=lambda p: -p["trending"])
    else:
        hot = sorted(posts, key=lambda p: p["date"], reverse=True)
    out = {"trending": listing("trending", hot[:CONFIG.get("trending_count", 8)])}
    for cat in SECTIONS:
        out[cat] = listing(cat, ranked(posts, cat))
    return out


def build_post(p, prev, nxt):
    sub = f'<p class="subtitle">{escape(p["subtitle"])}</p>' if p.get("subtitle") else ""
    origins = [(p["source"], p["url"])] + [(a["source"], a["url"]) for a in p.get("also_on", [])]
    orig = " · ".join(f'<a href="{escape(u)}">{SOURCE_NAMES[s]}</a>' for s, u in origins)
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
  <p class="meta">{orig} ↗</p>
</article>
<nav class="pager">{"".join(nav)}</nav>"""
    return page(f"{p['title']} · {CONFIG['site_title']}", body,
                description=p["blurb"], canonical=p["url"], depth=1, current=p["category"])


def main():
    posts = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts" / "style.css", OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
    pages = build_pages(posts)
    for key, _, href, _ in PAGES:
        (OUT / href).write_text(pages[key])
    for cat in SECTIONS:
        seq = ranked(posts, cat)
        for i, p in enumerate(seq):
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            (OUT / "posts" / f"{p['slug']}.html").write_text(build_post(p, prev, nxt))
    print(f"built {len(posts)} posts -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
