# Wikipedia Unsolved Problems Tracker

Wikipedia's *List of unsolved problems in mathematics*, frozen at 26 January 2024 (revision
1199136318), every problem on it researched individually, and each result since scored for whether
an AI system was involved.

The page has 467 bullets, ten of which are headings grouping the ones beneath them. **The
denominator is the other 457.**

**[Explore the data →](https://alexfogelson.github.io/wikipedia-unsolved-problems-tracker/)**

## Why

How much of recent mathematical progress involved AI is a proportion, so it needs a denominator
nobody chose after the fact. Collecting announced results gives a numerator and no denominator:
labs publish successes, journalists write about the dramatic cases, and the pile measures what got
reported. Here the denominator is fixed in advance, by a Wikipedia revision predating the results
being measured, and **every problem on it is researched whether or not anything happened to it.**

## Current version

`data/sonnet-2026-09-22/` — 457 problems researched in September 2026, one agent per problem, from
the raw records in `deepdive/mark_2026-09-22/` and `triage/2024-01/`. Earlier runs under `data/`
used a different method and are kept for comparison only.

Read `data/sonnet-2026-09-22/AUDIT.md` before relying on any number here: it covers what was
measured, what went wrong in the run, and the gaps that remain.

## Rebuilding

    python3 pipeline/fetch_list_revision.py      # network; -> data/<V>/page.wiki
    python3 pipeline/make_problem_keys.py        # network; -> problem_keys.md
    python3 pipeline/triage.py                   # optional; ~$90, one cheap agent per problem
    python3 pipeline/deep_dive.py --trial <name> # the research; one agent per problem
    python3 pipeline/merge_research.py --trial <name>
    python3 pipeline/judge.py --trial <name>     # optional; checks records for contradictions
    python3 pipeline/fetch_article_history.py    # network, cached; -> page_history.json
    python3 pipeline/build.py                    # -> data/<V>/, src/data.js, site/

Both research passes are resumable — a problem whose record exists is skipped — and read the API
key from `.secrets.json` (gitignored), a file holding `{"ANTHROPIC_API_KEY": "sk-ant-..."}`. The
`VERSION` constant must agree across `build.py`, `fetch_list_revision.py`,
`fetch_article_history.py` and `merge_research.py`.

## Publishing

    python3 pipeline/build.py
    pipeline/publish.sh [remote]                 # -> gh-pages, as index.html

The site is one self-contained file. `publish.sh` rebuilds `gh-pages` from scratch each time — just
`index.html` and `.nojekyll`, no parent commit — and force-pushes it. Point Settings → Pages at
that branch, root folder, once.

## Layout

- `site/` — the finished site: one HTML file, no server, no network.
- `src/` — its source: markup and CSS, the rendering code, and the dataset as `data.js`.
- `pipeline/` — the scripts above, and nothing else.
- `triage/<revision>/`, `deepdive/<trial>/` — the raw agent records, one JSON per problem.
- `data/<version>/` — the built dataset as JSON, CSV and SQLite.
- `DEEP_DIVE.md`, `TRIAGE_INSTRUCTIONS.md`, `JUDGE.md` — the prompt each pass runs under. The
  coding rules every record follows are stated in full in `DEEP_DIVE.md` §6.

## Licence

Code MIT, data CC BY-SA 4.0 (inherited from Wikipedia). See `LICENSE`.
