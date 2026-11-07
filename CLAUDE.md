# Blog repo — instructions for Claude Code

This site pulls Joshua's writing from LessWrong and Substack and sorts it onto four shelves. The
site is one academic-style **Publications** page (black on white, author legend * † ‡, every post
bylined "Joshua N. Brown†‡"). Tabs under the title switch pages: **Selected** (the landing page) shows
the top-scored posts regardless of shelf; each shelf tab lists its posts newest first, by year. Apply the first test that fits:

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
     "overall": "weighted total, 0-100 (rank.py recomputes it from scores)",
     "scores": {"novelty": 0-100, "evidence": 0-100, "rigor": 0-100, "craft": 0-100, "consequence": 0-100},
     "blurb": "under 8 words, plain, no hype words",
     "abstract": "60-90 words shown under the Abstract button: what the piece does, what it finds or argues, and (for research) its main limitation. Plain, faithful, no hype",
     "rationale": "two sentences, private"
   }
   ```
   The rubric has five metrics, each 0-100, weighted (also in `rankings.json` under `rubric`):

   | Metric | Weight | What it asks |
   |---|---|---|
   | novelty | 30% | Would an informed reader in that field learn something they couldn't get from three other sources? Restating a known idea well scores low no matter how well it's restated. |
   | evidence | 25% | Are the claims backed by data, controls and falsifiable predictions? Zero data means a low score even if the argument is correct. |
   | rigor | 15% | Does the piece name its own weaknesses accurately and at a cost to itself? Stated objections, withdrawn claims, admitted confounds. |
   | craft | 15% | Prose, structure, economy. Does it say it in the fewest good words? |
   | consequence | 15% | If fully true, how much does it change what anyone does? |

   For fiction and poetry, use `earned` (does it show rather than assert) in place of `evidence`
   and `control` (no unearned sentiment, no register breaks) in place of `rigor`. Weights stay the
   same. Honesty is 15%, not 50%: high rigor can't rescue low novelty and consequence.

   Calibration is absolute, not relative to this corpus: 90+ best in field (a NeurIPS or Nature
   paper, a story in The New Yorker); 80+ strong venue (Alignment Forum frontpage with real
   engagement, a top literary quarterly); 70 a good post people send each other; 60 competent,
   worth reading once; 50 fine for a personal blog; below 40 should not be on Selected (build.py
   keeps it off unless pinned). Anchors: The Trust Bank 66, Concept Injection 64, Love Doesn't
   Rust 63, Moral-Based Evaluation 51, The Formula for Success 21.
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
- `data/overrides.json` holds manual pin, hide, boost, category, blurb or abstract per slug.
- `.github/workflows/update.yml` runs all of the above every 6 hours and deploys to GitHub Pages.
