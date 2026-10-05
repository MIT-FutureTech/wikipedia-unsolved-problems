# Triage instructions

You are triaging **one** problem from Wikipedia's *List of unsolved problems in mathematics*.
Read this whole document, do the work in §4, write the record in §6, and stop. One problem, one
record, one run — do not look for other problems, do not carry anything over from another run.

---

## 1. Why this exists

A project is measuring how much of recent mathematical progress involved AI. The denominator is
fixed in advance so nobody can pick it: the 462 problems on Wikipedia's list of unsolved problems
as it stood on **26 January 2024**, before the results being measured. Every one of those problems
is researched, whether or not anything happened to it.

Researching 462 problems properly is expensive, so the work runs in two passes:

- **Pass one — this one.** A few searches per problem, deciding only *whether anyone should look
  properly*. Cheap, run on every problem.
- **Pass two — the deep dive.** Reads sources, dates results, classifies status and AI role. Run
  only on what this pass flags, plus a random sample of what it does not.

So your output is not a finding. It is a routing decision plus the raw material the deep dive
starts from. You are not deciding whether the problem was solved, by whom, whether the claim is
correct, or whether AI was involved. Someone else does that, from sources you will not read.

**A wrong flag costs one deep dive. A wrong pass costs a hole in the dataset that nothing
downstream can detect** — the deep dive never sees that problem, so nothing later can notice the
miss. The costs are not symmetric and your decisions should not be either.

---

## 2. Your problem

The harness supplies the fields below for the single problem in this run.

| Field | What it is |
|---|---|
| `key` | A slug such as `jacobian-conjecture`. Use it exactly as given; never re-slug it. |
| `statement` | The problem as the 26 January 2024 article words it, markup resolved to plain text. |
| `field` / `subfield` | The article's own section headings, not a classification anyone invented. |
| `parent` | Present only for a nested bullet, as ``sub of `<key>` ``, with the parent's statement. |

Two things about the statement. It is **Wikipedia's wording as of January 2024**, which may be
loose, may name the problem differently from the literature, and may be the only phrasing you have
— the named form ("Kakeya conjecture") is usually the better search term than the prose. And a
nested problem is often meaningless alone: if `parent` is present, read it first and search for the
sub-case, not the parent.

Grouping bullets — headings the article uses to bundle the problems under them — are not problems
and are filtered out before this pass. If one reaches you anyway, return a record with
`verdict: "skip"` and nothing else attempted.

**Work only from what you find yourself.** This repository holds earlier versions of this dataset —
research files under `data/`, tables in `pipeline/`, and records from previous triage runs. Those
are other agents' conclusions, and a verdict copied from one is not a check. Do not open them; if
you already have, search anyway and say so in `why`.

The frozen revision, if you need the surrounding context:

```
https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=1199136318
```

**The window is 26 January 2024 to today.** Anything earlier is outside it. That does not make it
irrelevant: a problem already settled *before* the list was frozen is a real finding for this
project (the list is stale and nobody removed it), so flag it rather than dropping it, and say in
`why` that the event looks pre-snapshot.

---

## 3. The question

> Has anything moved **this problem** — the one stated above, not the area around it — since
> 26 January 2024?

Size is not the test. A resolution counts, and so does a bound that moved by a little, a case
settled, a value computed. Progress is progress, and the deep dive is what decides how much it
amounts to.

**Scope is the test.** The result has to be about the problem as stated. Ask it as one question:

> Does this result change what a careful person would write in *this bullet's* entry?

If yes, it counts. If the honest answer is "no, but it is interesting work nearby", it does not.

Counts — the result speaks to the stated problem:

- a proof, disproof or counterexample, or a credible source calling the problem solved
- a bound or constant on **the problem's own quantity** improved, however slightly — where the
  quantity is what the bullet asks about, not merely a record in the same subject
- a case, dimension or class **of this problem** settled, leaving the rest of it open
- a claim of any of those that was later withdrawn — the claim is itself the event
- a source saying an AI system produced or contributed to any of the above

Does not count — the result is about something else, however close:

- a **different problem** that shares a name, a namesake, a technique or a neighbourhood
- a **variant, analogue or generalisation** with a different statement: the problem posed over
  other objects, in a setting it was not stated for, or with its hypotheses changed
- work that **uses, cites, surveys, reformulates or teaches** the problem without moving it
- a paper describing itself as a step toward the problem while proving something adjacent
- a **new example, record or extended search** where the question is whether something *exists* or
  whether there are *infinitely many*: a larger Mersenne prime found, a counterexample search
  pushed further, a table extended. See below.

**Existence and infinitude questions move only when they are answered.** "Are there infinitely
many X?" is not advanced by finding one more X, however hard the computation or however widely it
is reported — the question is about all of them, and the next one is as open as it ever was. The
same holds for a search verified to a larger limit, or a record table extended: those narrow where
an answer could hide, not whether it exists. Apply the test above and it comes out the same way,
since a new example does not remove any territory from the original question. A record only counts
where the record *is* the question, as in "what is the largest known …" or a bullet asking for the
value of a constant. Otherwise this is `none`, and `why` should say a new record was found and
that it leaves the question untouched.

The boundary between "a case of this problem" and "a related problem" is a judgement call, and it
is the judgement this pass is for. The rough test: a case of the problem is what you get by
*restricting* the stated question, so settling it removes territory from the original. A related
problem is what you get by *changing* the stated question, so settling it removes nothing —
however much the same mathematics is involved. When the sources genuinely leave you unable to tell
which you are looking at, that is what `possible` is for.

**The expected answer is "nothing", and it is a real answer.** The great majority of these problems
are still open and quietly so, including many with busy literatures. Reaching for something to
report is the main way this pass goes wrong; the second is deciding a search was not worth
running.

---

## 4. What to do

Between **three and five searches**, then stop. Phrase them however you judge best; the list below is
the shape of a good set, not a script.

1. **The problem by name**, plus a word that would only appear if it moved — `proof`, `solved`,
   `disproved`, `counterexample`, `resolved`.
2. **The problem by name, restricted to recent work** — add `2025`, `2026`, or `arXiv`.
3. **The objects, not the name**, if the name is obscure or ambiguous: the statement's own terms,
   which is how a paper would phrase it if the author did not use Wikipedia's name.
4. **The problem's own Wikipedia article**, if it has one. What its lead now says, and whether it
   has been edited since the snapshot, is a cheap and reliable signal.

Follow one obvious lead — open a page whose title looks decisive. **Do not start reading papers**;
that is the deep dive's job and it is the expensive one. If you find something that plainly settles
the routing decision, stop searching and write the record.

Worth noticing: a preprint that names *this* problem, an expert blog post working through a proof,
a change to the problem's Wikipedia article, a survey describing the problem as settled, a lab
announcement, a Lean or Coq repository for it.

### Three failure modes, all seen in testing

- **Search drifts to adjacent famous problems.** A query about an obscure prime family comes back
  full of twin primes and arithmetic progressions. If the results are about a *different* problem,
  that is `none` — not progress. Check that the hit names your problem, not its neighbourhood.
- **Old news reads as new.** Pages describing a result often bury the date, and recrawled or
  reposted pages look current. If you cannot pin a date, say so and flag it rather than guess.
- **A search that failed is not a search that came back empty.** If a tool errored, returned
  nothing usable, or you could not find a workable phrasing, say that in `why`. Silently recording
  `none` for a check that did not run is the worst outcome this pass can produce.

---

## 5. The verdict

| Verdict | Use when |
|---|---|
| `likely` | A specific post-snapshot source moves *this* problem, by §3's test: a resolution claim, a counterexample, a case of it settled, its own bound or value improved, or an AI system credited with any of those. |
| `possible` | Something may move it and you cannot tell — most often because you cannot tell whether the result is about this problem or a neighbouring one, or because you could not pin a date. Also when a search failed and you could not check. |
| `none` | You searched and found nothing that moves this problem. **This includes finding an active literature around it** — work on variants, analogues, related conjectures and applications. Say in `why` what you found and why it is beside the question. |
| `skip` | A grouping bullet reached you by mistake. Nothing else applies. |

`possible` is for **not being able to tell**, not for "there is activity here". If you can see
clearly that what you found is about a different statement than the one you were given, that is a
confident `none` — and recording it as `possible` sends the deep dive to read papers whose
irrelevance you had already established.

**When genuinely torn, go higher.** A wrong `none` is irreversible and a wrong `possible` costs one
deep dive — but that asymmetry is a reason to escalate real doubt, not to escalate by default.

Two judgements stay out of your hands. You are not assessing whether a claimed proof is
**correct** — a paper claiming a proof is a reason to escalate, never a reason to conclude, and
proofs get withdrawn. And you are not classifying the **AI role**: whether a model generated a
result, assisted a human or merely checked it is the deep dive's call. You decide only whether an
AI system appears in the story at all, which is a lower bar and deliberately so.

---

## 6. What to return

One JSON object, exactly the shape below. Write it to the output path the harness gives you; if it
gave you none, print it alone as the last thing in your reply, with no prose around it.

```jsonc
{
  "key": "kakeya-conjecture",              // verbatim, as given
  "verdict": "likely",                     // likely | possible | none | skip
  "why": "Several sources report the three-dimensional case proved by Wang and Zahl, Feb 2025.",
  "queries": [                             // every query you ran, verbatim, in order
    "Kakeya conjecture proof",
    "Kakeya set conjecture 2025 arXiv"
  ],
  "found": [                               // [] when nothing; one entry per distinct item
    {
      "url": "https://arxiv.org/abs/2502.17655",
      "title": "Volume estimates for unions of convex sets, and the Kakeya set conjecture in three dimensions",
      "date": "2025-02",                   // YYYY-MM, or YYYY, or null if you could not tell
      "note": "Preprint claiming the 3D case; not read."
    }
  ],
  "earliest_date_seen": "2025-02",         // earliest date on anything in `found`, else null
  "searched_wikipedia_article": true,      // did you look at the problem's own article
  "checked_on": "2026-09-19"               // today, YYYY-MM-DD
}
```

Rules on the record:

- **Every run produces one**, including every `none`. For most problems this record is the only
  evidence anyone ever looked, and a `none` with no queries in it is indistinguishable from work
  that was never done.
- **`why` is one or two sentences** and says what you saw, not what you concluded. For `none`:
  what you searched and what came back instead. For `possible`: precisely what you could not
  resolve.
- **Never truncate.** No eliding queries, no "and 3 others" in `found`.
- **Don't editorialise in `note`.** One line on what the item appears to be. You did not read it.

---

## 7. The check on this work

A random sample of the problems marked `none` gets the full deep dive regardless, so this pass's
miss rate is measured rather than assumed. That is why the `none` records have to be real: they are
the thing being audited, and a fabricated one corrupts the measurement of the measurement.
