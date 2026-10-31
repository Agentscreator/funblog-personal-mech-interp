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
    ROOT / "data" / "scores.json", ROOT / "data" / "overrides.json", ROOT / "data" / "rankings.json"])).hexdigest()[:8]
# Old URLs that people may have bookmarked or shared.
REDIRECTS = {"personal.html": "index.html"}
# Author markers, as on an academic publications page. Every post is solo, so Joshua is both.
LEGEND = [("*", "equal contribution"), ("†", "principal investigator"), ("‡", "corresponding author")]
AUTHOR = "Joshua N. Brown"
MARKS = "†‡"

# (key, tab label, file, one-line explainer). Each is its own page under the shared Publications
# header, like a filter tab. "selected" (the landing page) is the top-scored work across every
# shelf; every other key is a shelf (a post category).
PAGES = [("selected", "Selected", "index.html", "My best work, across every shelf."),
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
    rankings = json.loads((ROOT / "data" / "rankings.json").read_text())["posts"]
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
        p["abstract"] = o.get("abstract") or rankings.get(p["id"], {}).get("abstract") or excerpt(p)
        out.append(p)
    return out


def shelf(posts, cat):
    # Newest first, like a publications list; pinned posts still lead.
    pool = [p for p in posts if p["category"] == cat]
    newest = sorted(pool, key=lambda p: p["date"], reverse=True)
    return sorted(newest, key=lambda p: not p["pin"])


def excerpt(p, limit=70):
    # Stand-in abstract for posts not yet ranked: the subtitle plus the opening prose, skipping
    # short heading lines like "TL;DR" or "Prologue".
    words = p["subtitle"].split() if p.get("subtitle") else []
    for line in p.get("text", "").splitlines():
        if len(words) >= limit:
            break
        if len(line.split()) >= 8:
            words += line.split()
    text = " ".join(words[:limit])
    return text + ("…" if len(words) > limit else "")


def bibtex(p):
    word = next((w for w in p["slug"].split("-") if w not in {"the", "a", "an", "on", "of", "how", "in"}), "post")
    key = f"brown{p['date'][:4]}{word}"
    venue = ", ".join(SOURCE_NAMES[s] for s in venues(p))
    return (f"@misc{{{key},\n  author = {{Brown, Joshua N.}},\n  title = {{{p['title']}}},\n"
            f"  year = {{{p['date'][:4]}}},\n  howpublished = {{{venue}}},\n  url = {{{p['url']}}}\n}}")


def venues(p):
    return [p["source"]] + [a["source"] for a in p.get("also_on", [])]


def origins(p):
    return [(p["source"], p["url"])] + [(a["source"], a["url"]) for a in p.get("also_on", [])]


def byline():
    names = dict(LEGEND)
    marks = "".join(f'<span class="mark" title="{names[m]}">{m}</span>' for m in MARKS)
    return f'{AUTHOR}<sup class="marks">{marks}</sup>'


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


def page(title, body, *, description="", canonical="", depth=0, rel=None):
    rel = "../" * depth if rel is None else rel
    canon = f'<link rel="canonical" href="{escape(canonical)}">' if canonical else ""
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
  <a class="home" href="{link(rel, "index.html")}">joshua/</a>
  <p class="links">{links}</p>
  <p class="contact" id="contact">Say hi: <a href="mailto:{email}">{email}</a></p>
</header>
{body}
</main>
</body>
</html>
"""


def entry(p, rel=""):
    href = link(rel + "posts/", escape(p["slug"]) + ".html")
    venue = ", ".join(SOURCE_NAMES[s] for s in venues(p))
    actions = [f'<a href="{href}">Read</a>'] + [
        f'<a href="{escape(u)}" rel="noopener">{SOURCE_NAMES[s]} ↗</a>' for s, u in origins(p)]
    return f"""<li class="pub">
  <h4><a href="{href}">{escape(p['title'])}</a></h4>
  <p class="authors">{byline()}</p>
  <p class="venue"><em>{venue}</em>, {fmt_date(p['date'])} · {minutes(p)} min read</p>
  <div class="actions">
    <details><summary>Abstract</summary><p>{escape(p["abstract"])}</p></details>
    <details><summary>BibTeX</summary><pre>{escape(bibtex(p))}</pre></details>
    {" ".join(actions)}
  </div>
</li>"""


def section(key, posts, by_year):
    label, intro = next((l, i) for k, l, _, i in PAGES if k == key)
    if by_year:
        groups, out = {}, []
        for p in posts:
            groups.setdefault(p["date"][:4], []).append(p)
        for year, ps in groups.items():
            out.append(f'<h3 class="year">{year}</h3>\n<ul class="pubs">{"".join(entry(p) for p in ps)}</ul>')
        items = "\n".join(out)
    else:
        items = f'<ul class="pubs">{"".join(entry(p) for p in posts)}</ul>'
    return f"""<section id="{key}">
<h2>{label} <span class="count">{len(posts)}</span></h2>
<p class="intro">{escape(intro)}</p>
{items}
</section>"""


def featured(posts):
    # Best work regardless of shelf; these also stay on their own shelf. Unread posts can't be featured.
    pool = [p for p in posts if not p["provisional"] or p["pin"]]
    return sorted(pool, key=lambda p: (not p["pin"], -p["score"], p["date"]))[:CONFIG.get("featured_count", 6)]


def publications(groups, key):
    legend = "".join(f'<span><span class="mark">{m}</span> {escape(t)}</span>' for m, t in LEGEND)
    here = ' aria-current="page"'
    filters = "".join(f'<li><a href="{link("", href)}"{here if k == key else ""}>{escape(label)} '
                      f'<span class="count">{len(groups[k])}</span></a></li>' for k, label, href, _ in PAGES)
    body = f"""<h1>Publications</h1>
<p class="legend">{legend}</p>
<nav aria-label="Shelves"><ul class="filters">{filters}</ul></nav>
{section(key, groups[key], by_year=key != "selected")}"""
    title = "Publications" if key == "selected" else f"{LABELS[key]} · Publications"
    return page(f"{title} · {CONFIG['site_title']}", body, description=CONFIG["tagline"])


def build_post(p, prev, nxt):
    sub = f'<p class="subtitle">{escape(p["subtitle"])}</p>' if p.get("subtitle") else ""
    orig = " · ".join(f'<a href="{escape(u)}">{SOURCE_NAMES[s]}</a>' for s, u in origins(p))
    shelf = LABELS[p["category"]]
    nav = []
    if prev:
        nav.append(f'''<a class="prev" href="{link("", escape(prev["slug"]) + ".html")}">
  <span class="dir">← Newer in {shelf}</span><span class="title">{escape(prev["title"])}</span></a>''')
    if nxt:
        nav.append(f'''<a class="next" href="{link("", escape(nxt["slug"]) + ".html")}">
  <span class="dir">Older in {shelf} →</span><span class="title">{escape(nxt["title"])}</span></a>''')
    body = f"""<article>
  <a class="shelf" href="{link("../", FILES[p['category']])}">{shelf}</a>
  <h1>{escape(p['title'])}</h1>
  {sub}
  <p class="authors">{byline()}</p>
  <p class="meta">{fmt_date(p['date'])} · {minutes(p)} min read</p>
  <div class="prose">{p['html']}</div>
  <p class="meta">Also on {orig} ↗</p>
</article>
<nav class="pager" aria-label="More in {shelf}">{"".join(nav)}</nav>"""
    return page(f"{p['title']} · {CONFIG['site_title']}", body,
                description=p["blurb"], canonical=p["url"], depth=1)


def main():
    posts = load()
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "posts").mkdir(parents=True)
    shutil.copy(CSS, OUT / "style.css")
    (OUT / ".nojekyll").write_text("")
    groups = {"selected": featured(posts), **{cat: shelf(posts, cat) for cat in SECTIONS}}
    for key, _, href, _ in PAGES:
        (OUT / href).write_text(publications(groups, key))
    for old, new in REDIRECTS.items():
        new = link("", new)
        (OUT / old).write_text(f'<!doctype html><meta charset="utf-8"><title>Moved</title>'
                               f'<meta http-equiv="refresh" content="0; url={new}"><a href="{new}">Moved here</a>')
    # GitHub Pages serves this for a missing URL at any depth, so links must be absolute.
    root = urlparse(CONFIG["base_url"]).path.rstrip("/") + "/"
    (OUT / "404.html").write_text(page(f"Not found · {CONFIG['site_title']}", f"""<p class="intro">There's nothing at this address.</p>
<p><a class="back" href="{link(root, "index.html")}">See all publications →</a></p>""", rel=root))
    for cat in SECTIONS:
        seq = shelf(posts, cat)
        for i, p in enumerate(seq):
            prev = seq[i - 1] if i > 0 else None
            nxt = seq[i + 1] if i + 1 < len(seq) else None
            (OUT / "posts" / f"{p['slug']}.html").write_text(build_post(p, prev, nxt))
    print(f"built {len(posts)} posts -> {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
