#!/usr/bin/env python3
"""Pull every post from LessWrong and Substack into data/posts.json.

Standard library only, so it runs anywhere (locally or in GitHub Actions).
"""
import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config.json").read_text())
OUT = ROOT / "data" / "posts.json"
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/141.0 Safari/537.36",
    "Accept": "application/json, application/rss+xml, text/html;q=0.9, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def http_get(url, body=None):
    headers = dict(UA)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def http_json(url, body=None):
    return json.loads(http_get(url, body))


def cached_posts():
    return json.loads(OUT.read_text()) if OUT.exists() else []


# ---------------------------------------------------------------- sanitizing

ALLOWED = {
    "p", "h1", "h2", "h3", "h4", "h5", "h6", "em", "i", "strong", "b", "a",
    "ul", "ol", "li", "blockquote", "hr", "br", "img", "figure", "figcaption",
    "pre", "code", "sup", "sub", "table", "thead", "tbody", "tr", "th", "td",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
DROP_WITH_CONTENT = {"script", "style", "form", "button", "input", "svg", "iframe"}
DROP_CLASSES = ("subscription-widget", "subscribe", "button-wrapper", "footnote-anchor-")
KEEP_ATTRS = {"a": {"href"}, "img": {"src", "alt"}}
BOILERPLATE = re.compile(r"Thanks for reading!.*?support my work\.?", re.S)


class Sanitizer(HTMLParser):
    """Keep a small whitelist of tags and drop Substack's subscribe widgets."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0  # depth inside a dropped subtree
        self.stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class") or ""
        dropping = tag in DROP_WITH_CONTENT or any(c in cls for c in DROP_CLASSES)
        if self.skip or dropping:
            if tag not in VOID:
                self.skip += 1
            return
        if tag not in ALLOWED:
            return
        kept = "".join(
            f' {k}="{escape_attr(v)}"' for k, v in attrs
            if k in KEEP_ATTRS.get(tag, ()) and v and not v.lower().startswith("javascript:")
        )
        if tag == "a":
            kept += ' rel="noopener"'
        if tag == "img":
            kept += ' loading="lazy"'
        self.out.append(f"<{tag}{kept}>")

    def handle_endtag(self, tag):
        if self.skip:
            if tag not in VOID:
                self.skip -= 1
            return
        if tag in ALLOWED and tag not in VOID:
            self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(escape_text(data))


def escape_text(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def escape_attr(s):
    return escape_text(s).replace('"', "&quot;")


def sanitize(html):
    p = Sanitizer()
    p.feed(html or "")
    out = "".join(p.out)
    out = BOILERPLATE.sub("", out)
    return re.sub(r"<p>\s*</p>", "", out)


def to_text(html):
    t = re.sub(r"</(p|h\d|li|blockquote|figcaption)>|<br>", "\n", html)
    t = re.sub(r"<[^>]+>", "", t)
    t = t.replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"').replace("&amp;", "&")
    return re.sub(r"\n{3,}", "\n\n", t).strip()


# ---------------------------------------------------------------- sources

def fetch_lesswrong(slug):
    gql = "https://www.lesswrong.com/graphql"
    user = http_json(gql, {"query": '{ user(input:{selector:{slug:%s}}){ result { _id } } }' % json.dumps(slug)})
    uid = user["data"]["user"]["result"]["_id"]
    # authorIsUnreviewed:true is required, otherwise posts from new / unreviewed
    # accounts (and posts the mods rejected) are silently omitted.
    q = """{ posts(input:{terms:{view:"userPosts", userId:%s, limit:500, authorIsUnreviewed:true}}) {
      results { _id title slug postedAt baseScore commentCount wordCount pageUrl rejected
                contents { html } } } }""" % json.dumps(uid)
    res = http_json(gql, {"query": q})["data"]["posts"]["results"]
    posts = []
    for p in res:
        html = sanitize((p.get("contents") or {}).get("html"))
        posts.append({
            "id": f"lw-{p['_id']}",
            "source": "lesswrong",
            "slug": p["slug"],
            "title": p["title"].strip(),
            "subtitle": "",
            "date": p["postedAt"][:10],
            "url": p["pageUrl"],
            "words": p.get("wordCount") or len(to_text(html).split()),
            "engagement": {"karma": p.get("baseScore") or 0, "comments": p.get("commentCount") or 0},
            "lw_rejected": bool(p.get("rejected")),
            "html": html,
        })
    return posts


def fetch_substack(sub):
    # Substack's JSON API answers 403 to GitHub Actions' datacenter IPs, so fall
    # back to the RSS feed, which carries the full text of free posts.
    try:
        return fetch_substack_api(sub)
    except Exception as e:
        print(f"Substack API: {e}; trying RSS", file=sys.stderr)
        return fetch_substack_rss(sub)


def fetch_substack_rss(sub):
    xml = http_get(f"https://{sub}.substack.com/feed")
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    # RSS has no numeric post id or engagement counts: reuse what we already
    # know about a slug so its id (and therefore its ranking) stays stable.
    known = {p["slug"]: p for p in cached_posts() if p["source"] == "substack"}
    posts = []
    for item in ET.fromstring(xml).iter("item"):
        url = item.findtext("link").strip()
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        html = sanitize(item.findtext("content:encoded", "", ns))
        if not html:
            continue
        old = known.get(slug, {})
        posts.append({
            "id": old.get("id") or f"ss-{slug}",
            "source": "substack",
            "slug": slug,
            "title": item.findtext("title").strip(),
            "subtitle": (item.findtext("description") or "").strip(),
            "date": parsedate_to_datetime(item.findtext("pubDate")).date().isoformat(),
            "url": url,
            "words": len(to_text(html).split()),
            "engagement": old.get("engagement", {"likes": 0, "comments": 0, "restacks": 0}),
            "html": html,
        })
    return posts


def fetch_substack_api(sub):
    base = f"https://{sub}.substack.com/api/v1"
    archive, offset = [], 0
    while True:
        page = http_json(f"{base}/archive?sort=new&limit=50&offset={offset}")
        if not page:
            break
        archive += page
        offset += len(page)
    posts = []
    for a in archive:
        if a.get("audience") != "everyone":
            continue  # skip paywalled posts, we only have a preview
        d = http_json(f"{base}/posts/{a['slug']}")
        html = sanitize(d.get("body_html"))
        posts.append({
            "id": f"ss-{d['id']}",
            "source": "substack",
            "slug": d["slug"],
            "title": d["title"].strip(),
            "subtitle": (d.get("subtitle") or "").strip(),
            "date": d["post_date"][:10],
            "url": d.get("canonical_url") or f"https://{sub}.substack.com/p/{d['slug']}",
            "words": d.get("wordcount") or len(to_text(html).split()),
            "engagement": {"likes": d.get("reaction_count") or 0, "comments": d.get("comment_count") or 0,
                           "restacks": d.get("restacks") or 0},
            "html": html,
        })
    return posts


def norm_title(t):
    return re.sub(r"[^a-z0-9]", "", t.lower())


def main():
    posts = []
    for name, fn, arg in (("LessWrong", fetch_lesswrong, CONFIG.get("lesswrong_user")),
                          ("Substack", fetch_substack, CONFIG.get("substack_subdomain"))):
        if not arg:
            continue
        try:
            got = fn(arg)
            print(f"{name}: {len(got)} posts")
            posts += got
        except Exception as e:  # keep going if one source is down
            print(f"{name}: FAILED ({e})", file=sys.stderr)
            old = [p for p in cached_posts() if p["source"] == name.lower()]
            for p in old:
                p.pop("also_on", None)  # rebuilt below
            print(f"{name}: reusing {len(old)} cached posts", file=sys.stderr)
            posts += old

    # Cross-posted pieces: keep the Substack copy as primary, remember the LW link.
    by_title = {}
    for p in sorted(posts, key=lambda p: p["source"] != "substack"):
        key = norm_title(p["title"])
        if key in by_title:
            also = by_title[key].setdefault("also_on", [])
            if p["url"] not in {a["url"] for a in also}:
                also.append({"source": p["source"], "url": p["url"]})
            continue
        by_title[key] = p
    posts = list(by_title.values())

    for p in posts:
        p["text"] = to_text(p["html"])
        p["hash"] = hashlib.sha256((p["title"] + p["text"]).encode()).hexdigest()[:16]
    posts.sort(key=lambda p: p["date"], reverse=True)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(posts, indent=1, ensure_ascii=False))
    print(f"wrote {len(posts)} posts -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
