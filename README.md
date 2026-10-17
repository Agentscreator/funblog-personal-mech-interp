# funblog-personal-mech-interp

Joshua N. Brown's blog. It pulls automatically from
[LessWrong](https://www.lesswrong.com/users/joshua-n-brown) and
[Substack](https://substack.com/@joshbrown620328), and features the best work on two shelves:

- **Best Research**: AI safety, evaluation, decision-making
- **Best Personal**: short stories, poems, non-work essays
- **New & Trending**: engagement on each post, decayed by age

## How ranking works

There's no API key and it costs nothing to run.

- **Quality** scores come from Claude actually reading every post (`data/rankings.json`).
- **New posts** are placed on the right shelf automatically by similarity to labeled posts, and
  start at that shelf's median score. Likes, comments, restacks and karma can push them up. To give
  them a real score, open Claude Code in this folder and say **"rank new posts"** (see `CLAUDE.md`).
- **Manual control** lives in `data/overrides.json`:
  ```json
  { "posts": { "the-trust-bank": { "pin": true }, "the-formula-for-success": { "hide": true } } }
  ```
  The available fields are `pin`, `hide`, `boost` (±points), `category` and `blurb`.
