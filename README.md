# funblog-personal-mech-interp

Joshua N. Brown's blog, live at <https://agentscreator.github.io/funblog-personal-mech-interp>.
It pulls automatically from [LessWrong](https://www.lesswrong.com/users/joshua-n-brown) and
[Substack](https://substack.com/@joshbrown620328), hosts every post in full on its own page, and
sorts them onto four shelves:

- **Research**: experiments, simulations or data analysis, with results.
- **Perspectives**: arguments about AI, such as alignment, evaluation, and what AI changes.
- **Essays**: ideas not mainly about AI, such as decisions, incentives, and how to live.
- **Fiction & Poetry**: stories, poems and parables.

The landing page, **Featured**, shows the six highest-scoring posts from any shelf. They also stay
on their own shelf. Each shelf is sorted best first, and each post page links to the previous and
next post on its shelf and to the original on LessWrong or Substack.

Pieces cross-posted to both sites appear once. The Substack copy is kept, and engagement from both
copies counts.

## How ranking works

It needs no API key and costs nothing to run.

- **Quality** scores come from Claude reading each post in full (`data/rankings.json`). Each post's
  score is its quality plus a small bonus of up to 10 points for likes, comments, restacks and karma.
- **New posts** get a shelf guessed from their similarity to posts already labeled, and start at
  that shelf's median score. They cannot be featured until they have been read. To score them, open
  Claude Code in this folder and say **"rank new posts"** (see `CLAUDE.md`).
- **Edited posts** keep their old score until they are read again.
- **Manual control** lives in `data/overrides.json`, keyed by post slug:
  ```json
  { "posts": { "the-trust-bank": { "pin": true }, "the-formula-for-success": { "hide": true } } }
  ```
  The fields are `pin` (always listed first, and can be featured), `hide`, `boost` (± points),
  `category` and `blurb`.
- **Site settings** such as title, tagline, contact email, links and the number of featured posts
  are in `config.json`.

## Running it

```sh
python3 scripts/fetch.py   # pull posts into data/posts.json
python3 scripts/rank.py    # write data/scores.json (--pending lists unread posts)
python3 scripts/build.py   # render the static site into site/
```

Everything uses only the Python standard library. `.github/workflows/update.yml` runs these steps
every 6 hours and on each push to `main`, commits the refreshed `data/`, and deploys `site/` to
GitHub Pages.
