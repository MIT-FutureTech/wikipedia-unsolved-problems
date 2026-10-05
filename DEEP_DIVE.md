# Deep dive instructions

Pass two of two. You are given **one** problem from Wikipedia's *List of unsolved problems in
mathematics* as it stood on 26 January 2024. Find out what has happened to it since that date, and
how much of it involved an AI system.

One problem, one record, one run. Research it, write one structured record, stop. Do not look for
other problems and do not carry anything over from another run. Read this whole document first.

---

## 1. What this measures

The question behind the project is: **of the mathematical progress made since early 2024, how much
of it involved an AI system?**

That is a question about a proportion, so it needs a numerator and a denominator — how many
problems moved with AI involved, out of how many problems there were to move. The denominator is
the hard part, and getting it wrong is what makes most attempts at this question worthless.

The obvious approach is to collect the cases people talk about: a lab announces that a model solved
something, it gets written up, it goes on the pile. That produces a numerator and no denominator at
all. Labs publish their successes and not their failures, and journalists write about the dramatic
results and not the incremental ones, so the pile measures what got reported rather than what
happened. You cannot divide by a number nobody counted.

So the denominator is fixed in advance, by someone with no stake in the answer: a revision of
Wikipedia's list, frozen on 26 January 2024, before the results being measured. It holds 462
problems. Whoever wrote it was not thinking about AI, and it cannot grow to admit a result or
shrink to exclude an awkward one. **Every problem on it is researched, whether or not anything
happened to it and whether or not AI came near it.** Your problem is one of the 462, and your
record is one cell of that table.

A fixed denominator is only worth having if the numerator is gathered honestly, and there are two
ways to ruin it.

**Selection.** If results are found by searching for AI-related news, the number says more about
what gets written up than about what happened. A model producing a dramatic counterexample is
reported everywhere; a quiet improvement to a bound in an obscure corner of number theory is
reported nowhere. Treat a problem that turns out to have no AI anywhere near it as exactly as worth
your time as one that does. Most problems are in the first category.

**Pressure to find something.** The true answer is often "nothing happened", and that is a
successful result rather than a failed search. §5 says how to record it so that it counts as
evidence rather than as silence.

---

## 2. What you are given

| Field | What it is |
|---|---|
| `key` | A slug such as `jacobian-conjecture`. Use it exactly as given; never re-slug it. |
| `statement` | The problem as the frozen revision words it, markup resolved to plain text. |
| `field`, `subfield` | The article's own section headings, not a classification anyone invented. |
| `parent` | Present only for a nested bullet: the parent's key and statement. |
| `triage` | The pass-one record, described in §2.2. |

**A nested problem is not its parent.** Where `parent` is present, read it first: the bullet is a
sub-case and is often meaningless alone. Progress on the parent may or may not settle the child,
and the reverse, so research the statement you were given.

**The statement is Wikipedia's January 2024 wording.** It may be loose, and it may name the problem
differently from the literature. Search the standard name as well as the words in front of you.

### 2.1 The window

**The window is 26 January 2024 to today.** A result that appeared before 26 January 2024 did not
happen in the window, however recent the page describing it looks. That date is the frozen
revision's timestamp (`2024-01-26T03:23:06Z`, oldid `1199136318`) and every rule below turns on it.

You do not need the revision itself — the statement has been extracted for you. Open it only if a
nested problem is unintelligible without the bullets around it:

```
https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=1199136318
```

Never use the live article in its place. It changes constantly, and the method depends on the
denominator being frozen before the results being measured.

### 2.2 The triage record

A cheap pass swept all 462 problems and decided which were worth this attention. You are being sent
one it flagged, or one it did not as an audit sample. Its record has these fields and no others:

| Field | What it is |
|---|---|
| `verdict` | `likely`, `possible` or `none` — a routing decision, not a finding |
| `why` | One or two sentences on what it saw |
| `queries` | Every search it ran, verbatim |
| `found` | Items it turned up: `url`, `title`, `date` (or null), a one-line `note`. `[]` when nothing |
| `earliest_date_seen` | The earliest date on anything in `found`, or null |
| `searched_wikipedia_article` | Whether it looked at the problem's own article |
| `checked_on` | The date it ran |

**It is a pointer, not a finding.** It ran three to five searches and skimmed what came back,
opening a page only where a title looked decisive — it was told not to read papers, because that is
your job.

- **The `found` items** save you a search. Open them. Its `note` is a guess from a title and a
  snippet, and its `date` is often the date a page displayed rather than the date the work appeared.
- **The `queries`** tell you what was searched. If they look wrong — too broad, too narrow, the
  wrong name, Wikipedia's phrasing where the literature uses another — search again with better ones
  and set `triage_queries_replaced`.
- **`earliest_date_seen`** is a hint about where in time to look. Never copy it into `event`.
- **The verdict is not evidence.** Do not let `likely` push you toward finding something, and do not
  let `none` license a shallow pass. A `none` you were sent is a deliberate audit sample, and
  finding something in it is a valuable result rather than an embarrassment.
- **It applied §3.1's scope rule and may have applied it wrongly.** If what it dismissed as a
  variant is in fact a case of the problem, say so.

Where you contradict it in either direction, set `triage_disagreement` and explain in `summary`.
Those records measure the triage's error rate.

### 2.3 Everything in your record is yours

This dataset is built from scratch. The only things you may take as given are the mechanical
extractions above — key, statement, field, subfield, parent — which are the frozen revision's own
wikitext with the markup resolved. That is a parse, not a finding. **Every finding in your record
you establish yourself, from primary sources.**

**Do not read, cite or reuse any earlier run's research.** This repository holds previous versions
of this dataset: research files under `data/<version>/`, tables in `pipeline/` such as `status.py`,
`months.py` and `years.py`, and `AUDIT.md` files recording what an earlier agent concluded. Those
are another agent's judgements, made under rules that may not be these rules, and copying them
would make this run a restatement of that one rather than an independent measurement. Do not open
them; if you already have, say so in `summary` and establish the fact from the primary source
anyway.

---

## 3. The question

> What has happened to this problem since 26 January 2024?

Not "has anyone written about it", not "is it important". What has *happened*: has it been settled,
has a case of it been settled, has a bound moved, or has nothing occurred.

### 3.1 Which results count: scope, not size

**Size is not the test.** A resolution counts, and so does a bound that moved a little or a single
case settled. §6.1 is where you say how much it amounts to.

**Scope is the test.** The result has to be about the problem as stated in your bullet:

> Does this result change what a careful person would write in *this bullet's* entry?

A **case of the problem** is what you get by *restricting* the stated question — a dimension, a
class of objects, a special case. Settling it removes territory from the original, so it counts,
normally as `partial`.

A **related problem** is what you get by *changing* the stated question — a variant, an analogue,
the problem posed over different objects, a conjecture with different hypotheses, or a different
problem sharing a name or a namesake. Settling it removes nothing from the original, however much
the same mathematics is involved, and it is not a change to this problem. Where such work is all
you find, the status is `open` with `no_change_found` true, and `summary` says what you found and
why it is beside the question.

**An existence or infinitude question moves only when it is answered.** "Are there infinitely many
X?" is not advanced by one more X, by a search verified to a larger limit, or by a record table
extended. Those narrow where an answer could hide, not whether it exists. A record counts only
where the record *is* the question — a bullet asking for a largest known object or the value of a
constant.

Where the line between a case and a variant is genuinely unclear, classify on your best reading,
put the alternative in `competing_reading`, and say what would settle it. The ambiguity is a
finding; silently picking a side is not.

This is the rule the triage pass applied, restated so that both passes measure the same thing. A
numerator gathered under a looser rule than the filter that produced it does not match its
denominator.

---

## 4. Where to look

- arXiv listings and preprints, and their **submission dates**
- the authors' own account of how a result was obtained — the only acceptable basis for an AI claim
- expert digestions: Terence Tao's blog, the Matroid Union, Quanta, subject-specific blogs
- Lean or Coq repositories, and whether the proof still contains `sorry`
- lab announcements, technical reports and system cards
- the problem's own Wikipedia article, and what its lead now says
- problem databases covering the area, where one exists

**Open every source.** A search snippet is not a source; if you did not open the page, say so.
**Read past the abstract** — a paper's abstract may not disclose AI involvement that its
contribution statement or acknowledgements state plainly.

**A problem may not have its own article, and its link may go somewhere else.** Some bullets link
only a background topic, a related theorem, or the biography of the person the problem is named
after. Researching that article tells you nothing. Always search the problem's own name too.

Some publisher and lab sites refuse automated fetchers and return an error. That is not a dead
link: note it, fall back to secondary reports, and say in `summary` that you did.

---

## 5. When nothing happened

**This is the most important instruction here.** For most problems the correct answer is "no change
found", and a dataset where `open` might mean "nobody looked" is worthless as a denominator.

A record that finds nothing still has to carry evidence:

- `status` `"open"` and `no_change_found` true
- the searches you actually ran, verbatim
- where you looked — the arXiv listing, the Wikipedia article, Google Scholar, the relevant survey,
  any problem database covering the area
- any dead end you checked that plausibly could have held something
- your honest `confidence` that nothing escaped you
- a `summary` paragraph saying why you are satisfied nothing has happened

A well-evidenced "nothing happened" is as valuable as a resolution.

---

## 6. The rules

These decide the numbers. Apply them literally.

### 6.1 `status`

| Code | Means |
|---|---|
| `resolved` | Settled **and** digested by experts, or directly checkable by hand or computer algebra |
| `claimed` | A preprint, announcement or machine-checked certificate that experts have not yet digested |
| `partial` | A case of the problem settled — not a resolution |
| `progress` | A bound moved, or an instructive incident |
| `open_stale` | Settled **before** the frozen revision's date; recorded, never counted as a change |
| `open` | Still open. The default, and the right answer for most problems |

**`resolved` versus `claimed` turns on whether a human expert has read the argument.** Enough for
`resolved`: an expert digestion that works through the proof, acceptance by a journal of record, or
a published verification by named experts. Not enough: a preprint with no digestion however
prestigious the author, a press release without a manuscript, a machine proof whose only reader is
the compiler.

**A machine-checked certificate no expert has reviewed is `claimed`, however clean the check.**
Proof assistants have had soundness bugs, and a proof exploiting one compiles perfectly while
proving nothing. A green check is evidence about the kernel as much as about the mathematics.

**`open_stale` exists because the list is stale.** Some problems on it were settled before it was
frozen and nobody removed them. Date the first written argument against 26 January 2024 every time,
especially when a source says only "recently" — expect this more often than you would think. Where
there is both an earlier event and a later one, classify on the later and note the earlier.

`progress` also absorbs instructive failures. An AI claim announced and then withdrawn is
`progress`, `ai_role` `incident`, `resolution_direction` null, dated to the claim rather than to any
resolution — the problem itself did not move.

### 6.2 `ai_role`

| Code | Means |
|---|---|
| `generated` | An AI system produced the proof or counterexample; people checked it |
| `assisted` | Human-led work in which, **by the authors' own account**, an AI system produced part of the **mathematics that is in the result** — an argument, a construction, a case, a bound |
| `bound` | An AI system moved a bound on a problem that is still open |
| `incident` | An AI-produced claim that was announced or machine-verified, then withdrawn |
| `none` | No AI system — **or** its only contributions were checking, proofreading, debugging, suggesting strategies, or formalising what the humans produced. However many systems were used, and however much work they did |

**The word a source uses is not the code.** Papers say "assisted", "with the help of" and "we used"
for everything from writing the proof to fixing the LaTeX. Ask one question: *what did the model
produce that appears in the final result?* If the answer is "nothing the humans had not already
produced — it checked, tidied, formalised or suggested", the role is `none`, however warmly the
acknowledgement is worded and however many systems are named.

**`assisted` requires the authors' own account.** Not press coverage, not an inference from the
acknowledgements, not the fact that a model was in the room. Quote the sentence you relied on in
`ai.basis_quote` and give its URL. If you cannot quote anything, the role is `none`.

**`generated` versus `assisted` is about who did the mathematics.** Where the authors say the model
produced the proof or the counterexample and they verified it, that is `generated` — even with a
human first author, and even where a human designed the whole apparatus around the model. Wording
varies more than the underlying arrangement does: code what the authors say and put your
uncertainty in `competing_reading`.

**These are not AI involvement at all**: using a model to check a construction, to proofread, to
debug code, to explore proof strategies, or to write a formalisation. Where a formalisation is the
only AI contribution, set `formalisation_only` true and `ai_role` `none`. Expect human theorems
whose Lean proof was AI-assisted in a final phase; those are `none`.

**"Computer-assisted" usually does not mean AI.** SAT solvers, computer algebra, exhaustive search
and certified interval arithmetic are not AI systems under these codes. Read far enough to know
which you are looking at.

**`bound` is not a weak `generated`.** The problem is still open and what moved is a number.
Improving a partial result on a famous conjecture is not solving it and must never be counted as
one.

### 6.3 Dating

Date the **first public written argument** — the preprint, the announcement, the repository posting.
Never the journal publication, which can lag by years and will move results across the boundary of
the window. Record which kind of date it is in `event.kind`.

A result announced at a conference before the frozen date but written up after is a judgement call:
date it by the first written argument so that it counts, and say what you did in `summary`.

If you cannot establish a month, leave the month out and set `precision` to `year`. **Do not
substitute a midpoint.** A gap is honest; a fabricated July is not.

### 6.4 Counterexamples and direction

Two separate fields.

`counterexample` records whether the result *is* a counterexample and what the object is.

`resolution_direction` describes **the event the status rests on** — the result you recorded in
`event` — and not the problem's remaining openness. A case proved while the general conjecture
stays open is `confirmed`: the direction is about the result, not about how much of the problem is
left. Do not read it as "the problem was settled this way"; that is what `status` is for.

- `refuted` — the result goes against the conjecture, or answered the question against expectation
- `confirmed` — the result proves what was conjectured, or answers as expected
- `mixed` — the result settled several cases and they went both ways
- `null` — nothing was settled in either direction

**Required for `resolved`, `claimed` and `partial`.** A `partial` always has a direction, because
something was settled: say which way the settled piece went. Use `null` only for `progress`, `open`
and `open_stale`.

**A counterexample is an object that contradicts what the problem asserts.** Set
`counterexample.is_counterexample` true only then. An object that answers an existence question in
the *affirmative* — "is there a non-terminating game of beggar-my-neighbour?", and here is one — is
a witness, not a counterexample: `is_counterexample` false, and the direction is `confirmed`,
because the question was answered the way it was asked.

**Where it is a counterexample, the direction is `refuted` or `mixed`, never `confirmed`.** You
cannot exhibit an object that breaks a conjecture and record the result as confirming it. If the
problem asks for a bound rather than making a claim, and the object moves that bound without
contradicting anything, the direction may be `null` — but then it is not a counterexample either.

Keep them separate, because they come apart. A question answered in the negative is `refuted` with
no counterexample to a stated conjecture, and a counterexample to one case can leave the main
conjecture open.

This matters more than it looks. Finding one object that breaks a conjecture is a different
capability from proving a universal statement, and any analysis of AI's contribution needs to tell
them apart. A count of "problems solved" that pools the two hides the most interesting thing in the
data.

### 6.5 Naming the system

Name the specific systems credited, **exactly as the source names them**, including the tier or
version where the source gives one. Do not normalise, expand or tidy a name: a later pass matches
these strings to labs and release dates, and it can only do that if you recorded what the source
said.

- **Do not date the models.** Release dates are global facts researched once, not per problem.
- Where the source says the system was a pre-release, internal or unreleased build, or an agent
  harness rather than a shipped model, say so in `summary`. The name alone will not carry it.
- Where a source credits a lab but no system ("an OpenAI model"), record that string as given
  rather than guessing which model it was.
- **"Claude" is a common given name among mathematicians** — Claude Berge, Claude Shannon, Claude
  Chevalley, Claude Viterbo, Jean-Claude Fournier — and other model names have ordinary meanings
  too. Confirm that a name in mathematical prose refers to a model.

---

## 7. Traps

**Priority and attribution disputes are common here.** Record them in `disputes` rather than
picking a winner silently.

**A withdrawn claim is still an event.** Record it as `progress` / `incident`, dated to the claim.
Do not quietly drop it because it came to nothing.

**Retractions and updates postdate the paper.** A preprint that claimed a proof in March may have
been withdrawn in May. Check the arXiv version history and any comments before classifying.

---

## 8. What to return

One JSON object for the one problem you were given. Write it to the output path the harness gives
you; if it gave you none, print it alone as the last thing in your reply, with no prose around it.

**The record holds your findings and nothing else.** You do not echo the statement, field or parent
back — the harness has them. You do not record who ran you, on what model, or when; the harness
stamps that. §8.1 lists what other passes cover.

**Never truncate it.** Not the summary, not the source list, not the search log. A partial record
that looks complete is worse than an absent one, because nobody downstream can tell it was cut. If
you could not finish, name what is missing in `incomplete`.

**Every answer carries the links that establish it.** That is what the per-question `sources` arrays
are for: a reader must be able to see which URL supports the status, which supports the date, and
which supports the AI attribution. A single flat list at the bottom does not do that.

```jsonc
{
  "key": "jacobian-conjecture",        // exactly as given; the only input you echo

  "status": "partial",                 // resolved | claimed | partial | progress | open_stale | open
  "no_change_found": false,
  "outcome": "One sentence saying what happened.",
  "status_sources": ["…"],

  // The decisive event — the one the status rests on. Where a problem saw several, describe the
  // others in `summary` rather than inventing extra records.
  "event": {
    "date": "2026-07-19",
    "precision": "day",                // day | month | year
    "kind": "announcement",            // preprint | announcement | repository | journal | conference
    "predates_frozen_revision": false,
    "sources": ["…"]
  },

  "credited_humans": ["…"],

  "ai_role": "generated",              // generated | assisted | bound | incident | none
  "ai": {
    "basis_quote": "…",                // the authors' own words; required unless ai_role is none
    "formalisation_only": false,
    "disclosed_cost": null,            // where a source states compute, tokens or money
    "systems": ["…"],                  // names as the source gives them; no labs, no dates (§6.5)
    "sources": ["…"]
  },

  "counterexample": {
    "is_counterexample": true,
    "object": "…",                     // what the object is
    "explicit": true,                  // an exhibited object, not a non-constructive existence proof
    "verified_how": "…",
    "sources": ["…"]
  },
  "resolution_direction": "refuted",   // refuted | confirmed | mixed | null

  "disputes": [{"kind": "priority", "summary": "…", "sources": ["…"]}],

  // ---- the reasoning, which is the most valuable thing you produce
  "summary": "One paragraph: what was found, from which sources, and why it is classified this way.",
  "competing_reading": "The strongest case for a different classification.",
  "what_would_settle_it": "The evidence that would resolve the ambiguity.",
  "confidence": "high",                // high | medium | low

  // ---- every link you opened. Which answer each supports is recorded above; do not restate it.
  "sources": [{
    "url": "…",
    "title": "…",
    "type": "preprint",                // preprint | journal | blog | press_release | repository | encyclopedia | news
    "opened": true
  }],

  "search": {
    "queries": ["…"],                  // verbatim
    "places_checked": ["…"],
    "dead_ends": ["…"]
  },

  "incomplete": null,                  // what is missing, if anything; null when the record is whole
  "triage_disagreement": false,        // the triage's verdict was wrong, either way
  "triage_queries_replaced": false     // its queries were bad and you searched differently
}
```

### 8.1 What other passes cover

Deliberately not your job. Researching them here would mean answering the same question hundreds of
times:

| Fact | Why it is elsewhere |
|---|---|
| The year the problem was posed | Static, unrelated to what happened since 2024; one pass over all 462 |
| Whether the problem had its own Wikipedia article in January 2024 | A January 2024 fact about the encyclopedia, answerable in bulk |
| Each named system's lab and public release date | The same fact in every record naming it; researched once into a model table |
| Which problems imply which | Needs every record at once; a cross-pass after this one |
| Who ran this, on what model and when | The harness records it |
| Dataset-wide counts and the audit | Aggregated from the records; you cannot see the others, so do not summarise the dataset |

If one of these looks obviously wrong in passing — a model credited that could not have existed at
the date claimed, say — put it in `summary`. Do not research it.

### 8.2 Before you deliver, read back over your record

Not a program — a read-through. Check that:

1. The key is exactly the one you were given.
2. If the status is not `open`, it has an outcome, a date, and at least one link in
   `status_sources`.
3. If the only relevant event predates 26 January 2024, the status is `open_stale`.
4. Every result the record rests on is about the problem as stated, not a variant or a neighbouring
   problem (§3.1) — and where that was a close call, `competing_reading` says so.
5. Every `ai_role` other than `none` has a quote from the authors and a link in `ai.sources`.
6. Anything marked `formalisation_only` has `ai_role` `none`.
7. Every system is named as its source names it.
8. A `no_change_found` record lists the searches you ran.
9. No month was invented: anything with year-only precision has no month.
10. Every link cited by a per-question array also appears in `sources`.
11. Nothing was truncated.

Say in `summary` which of these you could not satisfy. A record that reports its own gaps is more
useful than one that claims to be clean.

---

## 9. Coverage and honesty

- **Do not silently narrow the work.** If you cannot research this problem to the standard above —
  a source you could not reach, a language you cannot read, a paywall — deliver the record with
  what you have, set `confidence` low, and say plainly what you could not do. A record that names
  its gap is usable; one that implies a completeness it does not have is not.
- **Do not let time pressure lower the bar.** A fast pass that marks the problem `open` without
  recording what was searched produces exactly the failure §5 exists to prevent: a denominator that
  looks complete and is empty.
- **One problem is the whole job.** There is no batch to get through and no quota to hit, so the
  pressure that makes a researcher skim does not apply. Spend the effort this problem needs.
