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

   Principles: grade only the text (no views, sales, awards, influence or author reputation);
   grade the unit as published; a score means the same on every shelf, because Selected mixes them.

   | Metric | Weight | Research & perspectives | Essays | Fiction & poetry |
   |---|---|---|---|---|
   | novelty | 30% | Would an informed reader in that field learn something they couldn't get from three other sources? Restating a known idea well scores low no matter how well it's restated. | Same | Would a well-read reader meet something new: premise, form, or specifics? A familiar shape with fresh specifics can reach the 70s; 80+ needs something new. |
   | evidence | 25% | Data, controls, falsifiable predictions. Zero data means a low score even if the argument is correct; claims are only as strong as their evidence. | **Support**: concrete cases, worked examples, checkable claims and predictions. Bare assertion scores low. | **`earned`**: shows rather than asserts; setups pay off, costs stay paid, resolutions aren't handed out. |
   | rigor | 15% | Names its own weaknesses accurately and at a cost to itself: stated objections, withdrawn claims, admitted confounds. | Same, plus the strongest version of the other side. | **`control`**: consistent register, no unearned sentiment, no cheap reversals, no narrator stating the moral. |
   | craft | 15% | Prose, structure, economy, and pull: fewest good words, and the reader wants the next line. | Same | Same, plus voice. Comedy that works counts here. |
   | consequence | 15% | If fully true, how much does it change what anyone does? | Same | **Resonance**: does it change how the reader sees something, and would they remember it a year later? Never reception. |

   Fiction stores `earned` and `control` in place of `evidence` and `rigor`; essays keep the key
   `evidence` but grade it as support. Weights stay the same. Honesty is 15%, not 50%: high rigor
   can't rescue low novelty and consequence.

   Process: score each metric on its own before the total, never back into a number. Length earns
   nothing; a twelve-line poem can score 90. Grade against the whole medium and note the genre in
   the rationale ("51 overall; near the top of progression fantasy"). If a metric sits more than
   10 points from the nearest comparable anchor, the rationale says why.

   Calibration is absolute, not relative to this corpus: 90+ best in field (a NeurIPS or Nature
   paper, a story in The New Yorker); 80+ strong venue (Alignment Forum frontpage with real
   engagement, a top literary quarterly); 70 a good post people send each other; 60 competent,
   worth reading once; 50 fine for a personal blog; below 40 should not be on Selected (build.py
   keeps it off unless pinned). Anchors: Do Claude Agents Peek 67, The Trust Bank 59, Love Doesn't
   Rust 58, Concept Injection 55, Moral-Based Evaluation 43, The Formula for Success 24. External
   fiction anchors: Gravity Falls 80, How to Train Your Dragon (film) 76, The Tale of Despereaux 75,
   How to Train Your Dragon (book 1) 64, The Beginning After the End 51.
5. Run `python3 scripts/rank.py && python3 scripts/build.py`, report where the new posts landed,
   and commit `data/` if the user asks.

Use `"rerank everything"` to re-read the whole corpus the same way. This is only worth doing when
the corpus has grown a lot.

## Layout

- `scripts/fetch.py` pulls both sources into `data/posts.json`. Stdlib only. LessWrong needs
  `authorIsUnreviewed:true` or posts from new or rejected accounts are hidden.
- `native/<slug>.md` holds posts written only for this site (`title:`/`date:` lines, a blank line,
  then paragraphs and `## ` headings). fetch.py adds them with source `site`.
- `scripts/rank.py` writes `data/scores.json` with quality (from rankings.json, or the shelf median
  if unread) plus trending (engagement decayed by age). It needs no API key.
- `scripts/build.py` turns everything into a static site in `site/`.
- `data/overrides.json` holds manual pin, hide, boost, category, blurb or abstract per slug.
- `.github/workflows/update.yml` runs all of the above every 6 hours and deploys to GitHub Pages.
