# Blog repo — instructions for Claude Code

This site pulls Joshua's writing from LessWrong and Substack and sorts it onto four shelves. The
landing page, **Featured**, shows the top-scored posts regardless of shelf; they also stay on their
own shelf. Apply the first test that fits:

- **research**: he ran something (an experiment, a simulation, an analysis of data) and reports
  results. Topic does not matter; an argument without results is not research.
- **perspectives**: an argument about AI, such as alignment, evaluation, or what AI changes in society.
- **essays**: an argument about ideas that are not mainly about AI, such as decisions, incentives,
  morality, or how to live.
- **fiction**: stories, poems, and parables. The tab is called "Fiction & Poetry".

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
     "category": "research" | "perspectives" | "essays" | "fiction",
     "overall": 0-100,
     "scores": {"originality": 0-10, "rigor": 0-10, "craft": 0-10, "depth": 0-10, "standalone": 0-10},
     "blurb": "under 8 words, plain, no hype words",
     "rationale": "two sentences, private"
   }
   ```
   Grade each post by its shelf's standard. Rigor for research means a reproducible method,
   controls and claims that stay inside the data; for perspectives and essays it means claims that
   are argued, not asserted; for fiction it means emotional honesty and precision. Penalise
   `standalone` when a piece largely repeats another post. Grade on the absolute scale in
   `rankings.json` (`scale`), not relative to this corpus: 90+ is best-in-genre published work, 80s
   would be published in a strong venue, 60s is good with clear weaknesses, 40s is notes or a weak
   draft. Leave headroom so improvement shows. Existing anchors are The Trust Bank 70, Moral-Based
   Evaluation 68, Love Doesn't Rust 60, and The Formula for Success 30.
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
