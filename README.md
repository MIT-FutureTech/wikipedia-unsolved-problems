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

`data/mark_2026-09-22/` — 457 problems researched in September 2026, one agent per problem. The
raw records it was built from sit beside it in `data/mark_2026-09-22/deepdive/`. Earlier runs
under `archive/data/` used a different method and are kept for comparison only.

Read `data/mark_2026-09-22/AUDIT.md` before relying on any number here: it covers what was
measured, what went wrong in the run, and the gaps that remain.

## Rebuilding

One stage at a time, in this order. `run.sh` takes a version name and runs the scripts in that
stage; there is deliberately no "run everything", because two of the stages cost real money and
the ones after them are worthless until you have read what the one before produced.

    V=my-run-2026-10-08
    pipeline/run.sh --version $V --stage fetch      # network; the slugs, the frozen list,
                                                   # the Jan-2024 titles, the scraped years
    pipeline/run.sh --version $V --stage research   # one agent per problem — BILLS AN API KEY
    pipeline/run.sh --version $V --stage judge      # one agent per record — subscription
    pipeline/run.sh --version $V --stage years      # agents; optional, and cached once run
    pipeline/run.sh --version $V --stage merge      # merge, date the models, merge again
    pipeline/run.sh --version $V --stage build      # -> data/<V>/, site/

Add `-n` to print the commands without running them, `--only KEY...` or `--sample N` to work on
part of the list, and `--check` to re-validate and re-collect a stage without launching an agent.

**The research pass reports findings and assigns no codes; the judging pass assigns them all.**
That is why judging is not optional: the merge refuses to write `research.json` while any record
lacks judged codes, because a problem built as `open` for want of a verdict cannot be told apart
from one researched and found open.

Every stage is resumable — a problem whose record exists is skipped — so re-running a command
retries only what failed. The research pass reads its API key from `.secrets.json` (gitignored),
a file holding `{"ANTHROPIC_API_KEY": "sk-ant-..."}`; the judging pass refuses to see that key and
runs on the logged-in Claude Code account instead.

Everything a run touches lives under `data/<version>/`, including that run's `problem_keys.md`, so
two runs never share a file. Each agent stage appends what produced it — the exact model id, the
prompt's hash, the commit — to `data/<version>/manifests/<stage>.json`.

## Publishing

    pipeline/run.sh --version $V --stage build
    pipeline/stage_7_publish_the_site/publish.sh [remote]   # -> gh-pages, as index.html

## Layout

- `site/` — the site, source and output together: `explorer_head.html` (markup and CSS),
  `explorer_app.js` (the rendering code) and `logos/`, plus the two files `build.py` writes — the
  dataset as `data.js` and the finished `unsolved_problems_explorer.html`, one HTML file with no
  server and no network.
- `pipeline/` — `run.sh`, one directory per stage named for what it does
  (`stage_2_research_each_problem/` and so on), `shared/` for the modules several stages import,
  and `prompts/`.
- `pipeline/prompts/DEEP_DIVE.md`, `pipeline/prompts/JUDGE.md` — the prompt each pass runs under.
  `DEEP_DIVE.md` §5 is what a research record must establish; `JUDGE.md` §3 is the arithmetic that
  turns a judge's per-event answers into the codes the dataset counts.
- `data/<version>/` — one run, self-contained: the built dataset as JSON, CSV and SQLite, the
  `problem_keys.md` it was keyed against, `manifests/` saying what produced each stage, and under
  `deepdive/` the raw agent records, judged copies and logs.

## Licence

Code MIT, data CC BY-SA 4.0 (inherited from Wikipedia). See `LICENSE`.
