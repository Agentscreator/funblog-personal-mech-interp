#!/usr/bin/env python3
"""Score every post. No API key, no network, standard library only.

Two numbers per post:

  quality   How good the piece is. Comes from data/rankings.json, which holds
            scores Claude assigned after actually reading each post (in a Claude
            Code session, see CLAUDE.md). A post nobody has read yet gets a
            provisional score: the median of its shelf. Text heuristics were
            tried and couldn't beat that (leave-one-out error was worse than
            guessing the median), so the script doesn't pretend to judge prose.
            Its shelf (research vs personal) *is* guessed reliably, by TF-IDF
            nearest neighbours against posts already labeled (16/17 in LOO).

  trending  Engagement velocity: likes, comments, restacks and LessWrong karma,
            decayed by age (Hacker News style). New posts that people respond
            to float up.

"Best" = quality + a small engagement bonus. Output: data/scores.json.

    python scripts/rank.py            # score everything
    python scripts/rank.py --pending  # list posts that still need a real read
"""
import argparse
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "data" / "posts.json"
RANKINGS = ROOT / "data" / "rankings.json"
SCORES = ROOT / "data" / "scores.json"

WORD = re.compile(r"[a-z']+")


def tfidf_vectors(posts):
    docs = {p["id"]: [w for w in WORD.findall((p["title"] + " " + p["text"]).lower()) if len(w) > 3]
            for p in posts}
    df = Counter(w for ws in docs.values() for w in set(ws))
    n = len(docs)
    out = {}
    for pid, ws in docs.items():
        v = {w: c * math.log(n / df[w]) for w, c in Counter(ws).items() if df[w] < n}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1
        out[pid] = {w: x / norm for w, x in v.items()}
    return out


def guess_category(pid, labeled, vectors, k=3):
    v = vectors[pid]
    sims = sorted(((sum(v.get(w, 0) * x for w, x in vectors[q].items()), cat) for q, cat in labeled.items()),
                  reverse=True)[:k]
    votes = Counter(cat for _, cat in sims)
    return votes.most_common(1)[0][0] if votes else "research"


def engagement(p):
    total = 0
    for e in [p.get("engagement", {})] + [a.get("engagement", {}) for a in p.get("also_on", [])]:
        total += e.get("likes", 0) + 2 * e.get("comments", 0) + 3 * e.get("restacks", 0) + max(e.get("karma", 0), 0)
    return total


def trending(p, today):
    age = max((today - date.fromisoformat(p["date"])).days, 0)
    return (1 + engagement(p)) / (age + 2) ** 1.5 * 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pending", action="store_true", help="list posts without a real read, then exit")
    args = ap.parse_args()

    posts = json.loads(POSTS.read_text())
    read = json.loads(RANKINGS.read_text())["posts"] if RANKINGS.exists() else {}
    # A read only counts if the text hasn't changed since.
    graded = {p["id"]: read[p["id"]] for p in posts if read.get(p["id"], {}).get("hash") == p["hash"]}
    pending = [p for p in posts if p["id"] not in graded]

    if args.pending:
        for p in pending:
            print(f"{p['id']}\t{p['slug']}\t{p['title']}")
        print(f"{len(pending)} post(s) need a read" if pending else "all posts have been read")
        return

    vectors = tfidf_vectors(posts)
    labeled = {i: g["category"] for i, g in graded.items()}
    shelf_median = {c: median([g["overall"] for g in graded.values() if g["category"] == c] or [60])
                    for c in ("research", "personal")}

    today = date.today()
    out = {}
    for p in posts:
        g = graded.get(p["id"])
        if g:
            cat, quality, source, blurb = g["category"], g["overall"], "read", g.get("blurb", "")
        else:
            cat = read.get(p["id"], {}).get("category") or guess_category(p["id"], labeled, vectors)
            quality, source, blurb = shelf_median[cat], "provisional", p.get("subtitle") or ""
        bonus = min(10, 3 * math.log1p(engagement(p)))
        out[p["id"]] = {
            "category": cat,
            "quality": quality,
            "quality_source": source,
            "engagement": engagement(p),
            "trending": round(trending(p, today), 3),
            "best": round(quality + bonus, 2),
            "blurb": blurb,
        }

    SCORES.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    for cat in ("research", "personal"):
        print(f"\n{cat}")
        for p in sorted((p for p in posts if out[p["id"]]["category"] == cat), key=lambda p: -out[p["id"]]["best"]):
            s = out[p["id"]]
            flag = "  (provisional, not read yet)" if s["quality_source"] == "provisional" else ""
            print(f"  {s['best']:6.1f}  {p['title']}{flag}")
    if pending:
        print(f"\n{len(pending)} post(s) not read yet. Open Claude Code in this repo and say 'rank new posts'.")


if __name__ == "__main__":
    main()
