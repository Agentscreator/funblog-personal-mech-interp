# Blog repo — instructions for Claude Code

This site pulls Joshua's writing from LessWrong and Substack, and features his best work on two
shelves: **research** (AI safety, evaluation, decision-making, incentives, analytical essays) and
**personal** (short stories, poems, reflective essays that are not about work).

## "Rank new posts"

When the user says "rank new posts" (or similar):

1. `git pull` then `python3 scripts/fetch.py` to get the latest corpus.
2. `python3 scripts/rank.py --pending` lists posts that have not been read (new or edited).
3. Read each pending post **in full** from `data/posts.json` (`text` field). Also skim the titles and
   blurbs of the already-ranked posts in `data/rankings.json` so scores stay calibrated against them.
4. For each pending post, add or replace its entry in `data/rankings.json` under `posts`, keyed by id:
   ```json
   "<id>": {
     "hash": "<copy from posts.json>",
     "category": "research" | "personal",
     "overall": 0-100,
     "scores": {"originality": 0-10, "rigor": 0-10, "craft": 0-10, "depth": 0-10, "standalone": 0-10},
     "blurb": "one sentence for the card, editor's voice, no hype words",
     "rationale": "two sentences, private"
   }
   ```
   Rigor for personal work means emotional honesty and precision, not evidence. Penalise
   `standalone` when a piece largely repeats another post. Use the full range and do not cluster
   everything at 70-85. Existing anchors are The Trust Bank 88, Mechanics of Association 90,
   Moral-Based Evaluation 87, and The Formula for Success 52.
5. Run `python3 scripts/rank.py && python3 scripts/build.py`, report where the new posts landed,
   and commit `data/` if the user asks.

Use `"rerank everything"` to re-read the whole corpus the same way. This is only worth doing when
the corpus has grown a lot.

## Layout

- `scripts/fetch.py` pulls both sources into `data/posts.json`. Stdlib only. LessWrong needs
  `authorIsUnreviewed:true` or posts from new or rejected accounts are hidden.
- `scripts/rank.py` writes `data/scores.json` with quality (from rankings.json, or the shelf median
  if unread) plus trending (engagement decayed by age). It needs no API key.
- `scripts/build.py` turns everything into a static site in `site/`.
- `data/overrides.json` holds manual pin, hide, boost, category or blurb per slug.
- `.github/workflows/update.yml` runs all of the above every 6 hours and deploys to GitHub Pages.
