# Data collection instructions

## What this project is

A controlled baseline for measuring how much of recent mathematical progress involved AI.

Frontier labs report their successes and not their failures, so you cannot read a rate of progress
from announcements alone. This project fixes that by taking a large, diverse list of genuinely hard
open problems that no AI lab selected — Wikipedia's *List of unsolved problems in mathematics* as it
stood on 26 January 2024 — freezing it, and then determining what has happened to each problem
since, and whether an AI system did the work. The frozen list is the denominator.

Your job is that determination. Everything else in the repo is plumbing around it — and the
plumbing is not ground truth either, so read it (see "Check the scripts" below).

## 1. Fetch the corpus

Fetch the raw wikitext of the frozen revision (oldid `1199136318`, 26 Jan 2024, 467 problems):

```
https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=1199136318&action=raw
```

Strip every `<ref>...</ref>` and self-closing `<ref ... />` from it, change nothing else — the
result must stay bullet-for-bullet identical to the revision — and save it as
`data/<version>/page.wiki`.

Fetch the same page at three later revisions as well; these are how you tell whether Wikipedia has
noticed a resolution yet, which is a finding in its own right:

| Snapshot | oldid |
|---|---|
| 2025-01 | `1272061095` |
| 2026-01 | `1335631179` |
| 2026-09 | `1374065418` |

Pick your own later revision if you are running after September 2026, and record its id and
timestamp in `pipeline/panel.py`.

## 2. Parse it

```
python3 pipeline/parse.py    # page.wiki -> problems_raw.json, solved_raw.json, titles.json
python3 pipeline/pages.py    # network, cached, resumable -> page_history.json
```

`parse.py` splits the page into the open-problem list and Wikipedia's own "solved in the past 30
years" section. `pages.py` establishes what stood at each linked title on the snapshot date — an
article, a redirect into a broader topic, or a redlink.

## Check the scripts

Do not assume the pipeline is correct because it runs. Every number in the final dataset passes
through code that was itself written by a model, and a parsing bug is indistinguishable from a
research error once it reaches the output. Before you trust an output, read the script that
produced it and verify its derivations against the wikitext by hand:

- `parse.py` — does the bullet split give the right name and description? Spot-check the odd
  shapes: nested bullets, bullets with no wikilink, bullets whose first link is a background topic
  rather than the problem, `<math>` in the middle of a name.
- `build.py` — `primary_wikilink` vs `wikipedia_url`, the `type` classifier, `named_after`, the
  Millennium/Hilbert/Smale/Landau flags. Confirm the counts it prints against the page itself.
- `panel.py` — the on-list pattern per problem, checked against the raw wikitext of each revision
  rather than against the previous run's table.
- `pages.py` — that a title reported as having its own article in January 2024 actually did.

Fix what is wrong, and say what you fixed. Recording a limitation you found but did not fix is
worth more than a silent workaround — write it up as described in §6.

## 3. Research every problem

This is the actual work, and it is one question asked 467 times:

> What has happened to this problem since 26 January 2024?

Answer it from primary sources, and open each one yourself rather than trusting a search snippet:

- arXiv preprints, and their submission dates
- the authors' own account of how the result was obtained — this is the only acceptable basis for
  an AI-assistance claim
- expert digestions (Terence Tao's blog, the Matroid Union, Quanta)
- Lean repositories, and whether the proof contains a `sorry`
- lab announcements and system cards
- Wikipedia's own later revisions of the page

Record a URL for every claim you make.

### Status codes

| Code | Means |
|---|---|
| `resolved` | Settled and accepted by experts, **or** directly checkable by hand or computer algebra |
| `claimed` | A preprint, announcement or machine-checked certificate that experts have not yet digested |
| `partial` | A listed sub-question or major special case settled — not a resolution |
| `progress` | A bound moved, or an instructive incident |
| `open_stale` | Already settled *before* the snapshot; shown, but never counted as a change |
| `open` | Still open. This is the default and needs no entry |

A Lean certificate that no human expert has reviewed is `claimed`, not `resolved`, however clean
the machine check.

### AI involvement codes

| Code | Means |
|---|---|
| `generated` | An AI system produced the proof or counterexample; people checked it |
| `assisted` | Human-led work in which, **by the authors' own account**, an AI system did a substantial part of the work |
| `bound` | An AI system moved a bound on a problem that is still open |
| `incident` | An AI-produced claim that was announced or machine-verified, then withdrawn |
| `none` | No AI system in the loop |

Using a model only to check a construction, proofread, debug code or write a Lean formalisation
does **not** qualify as `assisted`.

When a case is genuinely ambiguous, make your best guess, then flag it — say in the entry's `note`
what the call was, what the competing reading is, and what evidence would settle it. A flagged
judgment call can be reviewed later; a quietly downgraded one cannot.

### Model attribution

Name the specific systems credited, not just the lab, and give each one a **sourced** public
release date with the source named in a trailing comment.

- Never infer a release date from when a result appeared — that is an upper bound, not a release.
- A reasoning tier that no source dates separately inherits its base model's date and is marked
  as a tier rather than as a sourced date.
- Internal builds, agent harnesses and product-line names get no date at all: they never shipped
  as one model.
- Expect some results to legitimately predate their model's release. Pre-release and internal runs
  are real and the charts are built to show that gap, not hide it.

## 4. Save your findings as Python

Findings live in hand-written Python, never in a data file:

| File | Holds |
|---|---|
| `pipeline/status.py` | The research. Keyed by the problem's primary wikilink; each entry carries `status`, `outcome`, `year`, `by`, `ai`, `ai_system`, `note` and a `sources` list of URLs |
| `pipeline/years.py` | The year each problem was first posed |
| `pipeline/months.py` | The month of each resolution (of the preprint or announcement, not the journal) |
| `pipeline/panel.py` | Which problems moved on or off the list across the four revisions |
| `AI_MODELS` / `MODEL_RELEASE` in `pipeline/build.py` | Model → lab, and model → release date |

Only enter problems whose status actually changed; the rest default to `open`.

## 5. Build, then check what it printed

```
python3 pipeline/build.py
```

This regenerates **everything** under `data/<version>/` — JSON, CSV and SQLite — plus the site in
`src/` and `site/`. Those are outputs. Editing one by hand accomplishes nothing, because the next
build overwrites it; the Python is the only durable record of your research.

Then read the build's stdout before calling the work done. The script exits cleanly either way,
but each of these means an entry you wrote is not attaching to any record, so that finding is
silently absent from the dataset:

- `STATUS KEYS NOT MATCHED`
- `STATUS KEY MATCHED MORE THAN ONE RECORD`
- `MODELS WITH NO MODEL_RELEASE ENTRY`
- a non-empty `no month:`

## 6. Write `limitations.md` and `AUDIT.md`

Both go in `data/<version>/` beside the outputs, and both are required. They are what makes the
dataset usable by someone who was not you: the numbers alone cannot say which of them are soft.

### `limitations.md` — what the fields do not mean

One section per field or derived quantity that a reader could reasonably misread. For each one,
state the caveat, name the code that produces it (`build.py:58-66`), give the count, and say what
to use instead. Write it while you build, not afterwards — you will not remember which numbers
were soft once the dataset looks finished.

A section earns its place if a reader could quote the field in a claim it does not support. The
existing file covers, for example: `primary_wikilink` is set only when a bullet *opens* with a
wikilink, so `wikipedia_url` is not a substitute for it when asking about article coverage; a count
that holds today but not at the snapshot date; a hand review presented as if it were derived; and
fields that are partial by design. End with a "Still open" section listing what you know is
unresolved.

### `AUDIT.md` — how the research was checked

Written for whoever works on the dataset next, human or agent. Structure it as:

1. **Scope and ground rules** — which problems are in scope and which are deliberately excluded;
   how you dated events; the exact rules you applied for `resolved` vs `claimed` and for
   `assisted`. State these as rules, with examples of cases they exclude.
2. **Method** — what you actually did, with counts. How many entries were verified, against what
   kinds of source, how many searches and fetches, what was re-derived independently rather than
   carried forward, and which passes ran out of budget and are therefore not exhaustive.
3. **Headline findings** — what the check found: how many entries were fully correct, how many had
   a wrong status label, how many had a wrong attribution, AI role or date.
4. **Where Wikipedia disagrees with this dataset** — naming the revision you compared against.
5. **Judgment calls a reviewer may want to revisit** — every ambiguous case you flagged in §3,
   collected in one place, each with the competing reading and what would settle it.
6. **Known limits of this audit** — what you did not check, and what would be needed to check it.
7. **Files** — what you changed, and where.

Be specific and quantitative throughout: "23 fully correct, 8 with a wrong status label, 24 with a
wrong attribution, AI role or date" is useful; "most entries were correct" is not. If a pass was
incomplete, say so in the section that reports it rather than only in §6.
