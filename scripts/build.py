#!/usr/bin/env python3
"""Render data/posts.json + data/scores.json into a static site in site/."""
import hashlib
import json
import shutil
from datetime import date
from html import escape
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site"
CONFIG = json.loads((ROOT / "config.json").read_text())
CSS = ROOT / "scripts" / "style.css"
# GitHub Pages lets browsers cache every file for 10 minutes, so right after a deploy a phone can mix
# old and new pages. Every internal link carries this build id, so each deploy gets fresh URLs and
# all pages reached from one page come from the same build.
BUILD = hashlib.sha256(b"".join(f.read_bytes() for f in [
    Path(__file__), CSS, ROOT / "config.json", ROOT / "data" / "posts.json",
    ROOT / "data" / "scores.json", ROOT / "data" / "overrides.json"])).hexdigest()[:8]
# Old URLs that people may have bookmarked or shared.
REDIRECTS = {"personal.html": "index.html"}

# (key, nav label, file, one-line explainer). The first page is the landing page;
# every other key is a shelf (a post category).
PAGES = [("featured", "Featured", "index.html", "My best work, across every shelf."),
         ("research", "Research", "research.html", "Experiments and simulations, with results."),
         ("perspectives", "Perspectives", "perspectives.html", "Arguments about AI: alignment, evaluation, and what it changes."),
         ("essays", "Essays", "essays.html", "Ideas on decisions, incentives and how to live."),
         ("fiction", "Fiction & Poetry", "fiction.html", "Stories, poems and parables.")]
SECTIONS = [k for k, *_ in PAGES[1:]]
LABELS = {k: label for k, label, *_ in PAGES}
FILES = {k: href for k, _, href, _ in PAGES}
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
        if p["category"] not in SECTIONS:
            raise SystemExit(f"{p['slug']}: unknown category {p['category']!r}, expected one of {SECTIONS}")
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


def minutes(p):
    return max(1, round(p["words"] / 230))


def link(rel, href):
    # Link the home page by its folder, not index.html, so it matches the URL people land on.
    base = (rel or "./") if href == "index.html" else rel + href
    return f"{base}?v={BUILD}"


def page(title, body, *, description="", canonical="", depth=0, current="", rel=None):
    rel = "../" * depth if rel is None else rel
    canon = f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ""
    here = ' aria-current="page"'
    tabs = " ".join(f'<a href="{link(rel, href)}"{here if key == current else ""}>{label}</a>'
                    for key, label, href, _ in PAGES)
    email = escape(CONFIG["email"])
    links = " · ".join(['<a href="#contact">Contact</a>'] + [
        f'<a href="{escape(u)}" rel="me noopener">{escape(n)}</a>' for n, u in CONFIG["links"].items()])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="{escape(description)}">
{canon}
<link rel="icon" href="data:,">
<link rel="stylesheet" href="{link(rel, 'style.css')}">
</head>
<body>
<main>
<header>
  <a class="name" href="{link(rel, "index.html")}">{escape(CONFIG["site_title"])}</a>
  <p class="links">{links}</p>
  <p class="contact" id="contact">Say hi: <a href="mailto:{email}">{email}</a></p>
  <nav class="tabs" aria-label="Sections">{tabs}</nav>
</header>
{body}
</main>
</body>
</html>
"""


def entry(p, shelf=False):
    note = f'<span class="blurb">{escape(p["blurb"])}</span>' if p["blurb"] else ""
    info = ([LABELS[p["category"]]] if shelf else []) + [short_date(p["date"]), f"{minutes(p)} min read"]
    return f"""<li><a class="item" href="{link("posts/", escape(p['slug']) + ".html")}">
  <span class="title">{escape(p['title'])}</span>
  {note}
  <span class="info">{" · ".join(info)}</span>
</a></li>"""


def listing(key, posts):
    label, intro = next((l, i) for k, l, _, i in PAGES if k == key)
    body = f"""<p class="intro">{escape(intro)}</p>
<ul class="list">{"".join(entry(p, shelf=key == PAGES[0][0]) for p in posts)}</ul>"""
    title = CONFIG["site_title"] if key == PAGES[0][0] else f"{label} · {CONFIG['site_title']}"
    return page(title, body, description=CONFIG["tagline"], current=key)


def featured(posts):
    # Best work regardless of shelf; these also stay on their own shelf. Unread posts can't be featured.
    pool = [p for p in posts if not p["provisional"] or p["pin"]]
    return sorted(pool, key=lambda p: (not p["pin"], -p["score"], p["date"]))[:CONFIG.get("featured_count", 6)]


def build_pages(posts):
    out = {"featured": listing("featured", featured(posts))}
    for cat in SECTIONS:
        out[cat] = listing(cat, ranked(posts, cat))
    return out


def build_post(p, prev, nxt):
    sub = f'<p class="subtitle">{escape(p["subtitle"])}</p>' if p.get("subtitle") else ""
    origins = [(p["source"], p["url"])] + [(a["source"], a["url"]) for a in p.get("also_on", [])]
    orig = " · ".join(f'<a href="{escape(u)}">{SOURCE_NAMES[s]}</a>' for s, u in origins)
    shelf = LABELS[p["category"]]
    nav = []
    if prev:
        nav.append(f'''<a class="prev" href="{link("", escape(prev["slug"]) + ".html")}">
  <span class="dir">← Previous in {shelf}</span><span class="title">{escape(prev["title"])}</span></a>''')
    if nxt:
        nav.append(f'''<a class="next" href="{link("", escape(nxt["slug"]) + ".html")}">
  <span class="dir">Next in {shelf} →</span><span class="title">{escape(nxt["title"])}</span></a>''')
    body = f"""<article>
  <a class="shelf" href="{link("../", FILES[p['category']])}">{shelf}</a>
  <h1>{escape(p['title'])}</h1>
  {sub}
  <p class="meta">{fmt_date(p['date'])} · {minutes(p)} min read</p>
  <div class="prose">{p['html']}</div>
  <p class="meta">Also on {orig} ↗</p>
</article>
<nav class="pager" aria-label="More in {shelf}">{"".join(nav)}</nav>"""
    return page(f"{p['title']} · {CONFIG['site_title']}", body,
                description=p["blurb"], canonical=p["url"], depth=1, current=p["category"])


def main():
    posts = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(CSS, OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
    pages = build_pages(posts)
    for key, _, href, _ in PAGES:
        (OUT / href).write_text(pages[key])
    for old, new in REDIRECTS.items():
        new = link("", new)
        (OUT / old).write_text(f'<!doctype html><meta charset="utf-8"><title>Moved</title>'
                               f'<meta http-equiv="refresh" content="0; url={new}"><a href="{new}">Moved here</a>')
    # GitHub Pages serves this for a missing URL at any depth, so links must be absolute.
    root = urlparse(CONFIG["base_url"]).path.rstrip("/") + "/"
    (OUT / "404.html").write_text(page(f"Not found · {CONFIG['site_title']}", f"""<p class="intro">There's nothing at this address.</p>
<p><a class="back" href="{link(root, "index.html")}">See my best work →</a></p>""", rel=root))
    for cat in SECTIONS:
        seq = ranked(posts, cat)
        for i, p in enumerate(seq):
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            (OUT / "posts" / f"{p['slug']}.html").write_text(build_post(p, prev, nxt))
    print(f"built {len(posts)} posts -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
