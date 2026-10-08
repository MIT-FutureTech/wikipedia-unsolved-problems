# Instructions

You are given **one** problem in mathematics, which at one point was unsolved, but whose current state is unknown to the author of this document. Your task is to collect information about this problem, what has happened to it since January 2024, and any information about AI involvement. The problem is from Wikipedia's *List of unsolved problems in mathematics* (as it stood on 26 January 2024).

**Your job is not to classify the problem. It is to find out what happened and write down what you found, with the evidence.** Your record is then read by a second pass, and that pass is the one that decides how the problem is finally counted: how much of the problem the result settles, whether anyone qualified has checked it, whether it should be believed, and whether an AI system did the mathematics. It cannot search; it sees only what you wrote. Anything you learned and did not record is lost, and anything you decided instead of recorded is a decision it cannot check.

So the question in your mind is never *which label fits this?* It is **what would someone need to see to decide?** Where you find yourself weighing a call, write down both sides and what each rests on.

---

## 1. What this measures

The question behind the project is: **of the mathematical progress made since early 2024, how much of it involved an AI system?**

That is a question about a proportion, so it needs a numerator and a denominator — how many problems moved with AI involved, out of how many problems there were to move. The better the denominator, the better the signal. Without a denominator, you cannot know whether the successes are just a product of selection bias, since we see the successes, not the failures.

We fix the denominator to be Wikipedia's List of Unsolved Problems in Mathematics, frozen on 26 January 2024. It holds 457 problems. Whoever wrote it was not thinking about AI, and it cannot grow to admit a result or shrink to exclude an awkward one. Your problem is one of the 457, and every one of the 457 is researched regardless of whether it was solved and regardless of AI usage.

A fixed denominator is only worth having if the numerator is gathered properly. Here are failure modes we want to avoid:

**Selection.** If results are found by searching for AI-related news, the number says more about what gets written up than about what happened. A model producing a dramatic counterexample is reported everywhere; a quiet improvement to a bound in an obscure corner of number theory is reported nowhere. Hence, even if a problem does not have AI anywhere near it, it is just as worth researching for our purposes — and most of the 457 are of exactly that kind.

**Pressure to find something.** The true answer to how a problem has moved is often "nothing happened." That is a perfectly successful result, not a failure. §4.1 says how to record it so that it counts as evidence rather than as silence.

**Deciding instead of reporting.** A record that says only *what the researcher concluded* cannot be revisited when the rules classifying problems downstream change — and they do change. A record that says what was found, who said it, and where, will still be helpful for later decisions.

---

## 2. The research question

> What has happened to this problem since 26 January 2024?

Not "has anyone written about it", not "is it important". What has *happened*: has it been settled, has a case of it been settled, has a bound moved, or has nothing occurred.

### 2.1 Which results count: scope, not size

**Size of the result is not the test.** A resolution counts, but so does a bound that moved a little or a single case settled. How far a result goes is recorded in §5.1 and weighed later; it is not a filter on what you report.

**Scope is the test.** The result has to be about the problem as stated in your bullet:

> Does this result change what a careful person would write in *this bullet's* entry?

A result on an analogue, a different-hypotheses version, a stronger or weaker form, or a different problem sharing a name or a namesake, settles nothing here, however much the same mathematics is involved. Where such work is all you find, still collect it — say what it was and say plainly that it is about a different question.

The distinction that is genuinely hard, and that v1 of this dataset got wrong in both directions:

> **Did a quantity named in the problem statement move? Or did some set of newly confirmed instances grow?**

- On the **abc conjecture**, an exceptional-set bound was once declined as "not the conjecture itself". That was wrong: the number of exceptions is the conjecture's own quantity, so the bound moves it.
- On the **1-3-2-3 conjecture**, a census of posets on at most 14 elements was once recorded as the event. That was wrong the other way: finitely many instances of a universal claim move nothing.
- **Collatz** is the clean case: verification to 2⁷¹ is one more instance and counts for nothing, since the conjecture applies to all numbers.

You are not asked to resolve which side a borderline case falls on. You are asked to record, in the bullet's own words, what the bullet asks for and what the result delivers, so that the call can be made and audited later. This is merely context so you can clearly direct and frame your research.

---

## 3. What you are given

| Field | What it is |
|---|---|
| `key` | A slug such as `jacobian-conjecture`. Use it exactly as given; never re-slug it, since it will be used downstream. |
| `statement` | The problem, as the frozen revision words it, markup resolved to plain text. This is in case the slug has any ambiguity. |
| `field`, `subfield` | Fields and subfields are derived from the original Wikipedia article's headings. |
| `parent` | For a nested bullet on the Wikipedia page, this is the parent's key and statement. |

**A nested problem is not its parent.** Where `parent` is present, read it first: the bullet is a sub-case and is often meaningless alone. Progress on the parent may or may not settle the child, and the reverse, so research the statement you were given.

**The statement is Wikipedia's January 2024 wording.** It may be loose, and it may name the problem differently from the literature. Make sure the results match the description of the problem, not just the standard name.

---

## 4. What sources to use

- arXiv listings and preprints, including their **submission dates** and their **version history**
- expert digestions: Terence Tao's blog, the Matroid Union, Quanta, subject-specific blogs
- Lean or Coq repositories, and whether the proof still contains `sorry`
- lab announcements, technical reports and system cards
- the problem's own Wikipedia article, and what its lead now says
- problem databases covering the area, where one exists
- for AI usage, the authors' own account of how a result was obtained — the only acceptable basis for an AI claim
- **anything written about the result after it appeared**: a published comment, a blog post working through it, a later paper that cites it — or later papers that still call the problem open and do not cite it at all, which is itself a finding worth recording

**Open every source.** A search snippet is not a source; if you did not open the page, say so. **Read past the abstract** — a paper's abstract may not disclose AI involvement that its contribution statement or acknowledgements state plainly.

**A problem may not have its own article, and its link may go somewhere else.** Some bullets link only a background topic, a related theorem, or the biography of the person the problem is named after. Researching that article tells you nothing. Always search the problem's own name too.

Some publisher and lab sites refuse automated fetchers and return an error. That is not a dead link: note it, fall back to secondary reports, and say in `summary` that you did.

### 4.1 When nothing happened

For most problems the correct answer is that nothing has happened, and a dataset where "open" might mean "nobody looked" is worthless as a denominator.

A record that finds nothing still has to carry evidence:

- `nothing_found` true, and an empty `events` array
- the searches you actually ran, verbatim
- where you looked — the arXiv listing, the Wikipedia article, Google Scholar, the relevant survey, any problem database covering the area
- any dead end you checked that plausibly could have held something
- your honest `confidence` that nothing escaped you
- a `summary` paragraph saying why you are satisfied nothing has happened

A well-evidenced "nothing happened" is as valuable as a resolution.

---

## 5. What to establish

Everything here is about an **event**: a preprint, announcement, repository posting, formalisation or published paper bearing on this problem. Record each one separately, including the ones you expect to be discounted — a withdrawn claim, a result on a neighbouring problem, a search to 10¹⁸. A discarded event with a reason is evidence; a missing one is a hole.

### 5.1 What happened, when, and what it establishes

What was claimed or shown, by whom, and where it appeared.

**Date the first public written argument**, and not the journal publication, which can lag by years and would move a result across the boundary of the window. That one rule settles the awkward cases too: a talk given before the argument was written up is dated to the write-up, and a preprint re-posted with minor changes keeps the date of the version that first carried the mathematics. Where you cannot pin down the month, leave it out and say so rather than guessing at one.

Then say what the result establishes **in relation to the problem itself**. Did it settle the problem entirely, or a restricted case of it — a range of dimensions, a class of objects, one of several parts the problem asks about? Did it move a quantity the problem asks for while leaving the problem open? Did it check finitely many instances of a claim about infinitely many? Did it answer a changed version of the question — an analogue, different hypotheses, a stronger or weaker form?

Three fields carry this, and the judging pass reads the gap between them to decide how far the result goes. You are not asked to measure that gap, only to make it visible.

**`problem_asks` is written once, for the problem, before you weigh any event.** Unpack the statement into its parts and list them: a statement naming two conjectures asks two things, a statement listing fourteen constants asks fourteen. Write it from the statement alone — the commonest way this goes wrong is a researcher who has found a result for one dimension quietly writing down a problem about one dimension, which makes a case look like a resolution. If the result you found turns out to answer only part of what you listed, that is the finding.

**`delivers` and `remains` are per event.** `delivers` is what that event establishes, carrying every restriction it comes with — the dimensions it covers, the hypotheses it adds, the class it is confined to. `remains` names which parts of `problem_asks` are still open afterwards. Between them they should account for everything `problem_asks` lists.

### 5.2 Who has checked it, and whether there is reason to doubt it

**Whether a qualified human has worked through the argument and said so in public.** The previous run under-reported this, so look for it specifically.

Per entry in `checked_by`: who they are, why they are in a position to judge, what they did, and where they said it — a journal of record accepting it, named experts publishing a verification or a digested rewrite, a blog post working through the proof, a doctoral committee approving the thesis that contains it.

- **Name them.** "Experts have reviewed it" is not usable.
- Review sites and AI referees (Pith Review, Refine, a lab's own "adversarial review panel") are not human readings. Record them with `automated` true.
- A clean Lean or Coq build is not a human reading either. Put the build and whether it still contains `sorry` in `machine_checked`, separately from who has read it.
- **Silence is a finding.** Where a claimed landmark has sat a year with no uptake, say so and say how long.
- Where the result is an object anyone can check directly — a polynomial map, a graph, a configuration — say what it is and how it checks.

**Record reasons to doubt the result where they exist, and nothing where they do not.** Not having been reviewed is not a reason to doubt: that is the normal state of recent work, and the paragraph above already records it. What is wanted here is something active — a venue that reviews nothing, authors with no relationship to the field, later papers that still describe the problem as open and do not cite it, scope that grew between versions, a method the problem is known to resist, a specific error identified in a key step that nobody has answered, or a withdrawal, retraction or concession. Record what you find and leave the weighing to the later pass, which does it once instead of 457 times.

### 5.3 Which way it went, and whether an object was found

Critical to our analysis is **which way the result cuts** relative to the problem statement. Does it prove what was conjectured? Does it answer the question as expected? Does it provide a counterexample? Do different parts of the problem settle in different ways? What makes an object a counterexample is what the problem asks, not how impressive the object is:

> **Borsuk's problem** reaches you as a question about upper and lower bounds on the number of smaller-diameter pieces needed to cover a bounded n-dimensional set. A 321-point configuration in R⁶³ that cannot be covered by 64 such pieces pushed the smallest dimension where this is known to fail from 64 down to 63 — and it was produced with GPT-5.5 Pro. Record the configuration, and record that it cannot be covered by 64 pieces: that is what tells the later pass it cuts against Borsuk's conjecture. But the question as you were given it asks for bounds rather than asserting the conjecture, so what this result did was move a bound, not settle the question either way. Record both facts; reconciling them is the later pass's job.

By contrast, *"is there a non-terminating game of beggar-my-neighbour?"* was answered by exhibiting a pair of 26-card hands that loop forever. There the object is exactly what the question asked for, so it contradicts nothing — and the result went the way the question pointed.

Where an object was exhibited, `object` is one piece of prose saying what it is, what it shows, and whether it is explicit or comes from a non-constructive existence proof. Be concrete: the polynomial map itself, the cubic graph on 112 vertices, the 321-point configuration. The later pass cannot look the object up, so an entry that names it without saying what it shows is of no use to anyone. **Whether the object contradicts what the problem asserts is that pass's call, not yours** — `object` and `direction` are what it reads to make it. How the object was checked belongs in `machine_checked`, `directly_checkable` or `checked_by` (§5.2), not here.

### 5.4 Whether an AI system was involved, and what it did

The core question we want to answer: was an AI system involved in the substantive development of the mathematics. It has two parts, with separate answers and separate fields — whether a system was involved at all, and whether what it produced is in the result.

**Whether one was involved at all** is a question for the sources, not something to assume in either direction. Do not read a system into an acknowledgement that names none, and do not pass over one that is named because its involvement looks incidental. Where nothing in the sources names a system, set `ai.none_found` true; where something does, leave it false and read far enough to say what the system did. Either answer is a finding.

**Whether what it produced is in the result** is the test for `ai.systems`: is the contribution load-bearing — mathematics the work would have had to establish some other way had the system not supplied it — as against work done around the mathematics.

Checking a proof the humans had written, proofreading, debugging code, searching the literature and formalising an argument already proven by humans are worth recording, but are not the AI involvement we are looking for, and should be noted as such. A system whose involvement stopped at these does not go in the final response's `ai.systems` — but it was still involved, so `none_found` stays false and `summary` says what it did.

At the other end, where the authors credit a model with the idea the proof turns on, that is load-bearing however casually they phrase it. Record it and let the later pass weigh it.

**Every system you put in `ai.systems` needs the authors' own account of what it did** — not press coverage, not an inference from the acknowledgements. Quote their sentence in `basis_quote` and give its URL; where nothing is quotable, say so in `summary` rather than reasoning from circumstance. Sources say "assisted" and "with the help of" for everything from writing the proof to fixing the LaTeX, so record what the quote literally says and no more. A human first author settles nothing: where the authors say the model produced the proof and they verified it, record that.

**"Computer-assisted" usually does not mean AI.** SAT solvers, computer algebra, exhaustive search and certified interval arithmetic are not AI systems. Read far enough to know which you have, and say which.

**Name each system exactly as the source names it**, including the tier or version, because a later pass matches these strings to labs and release dates:

- Do not normalise, expand or tidy a name, and do not date the models — release dates are global facts researched once.
- A lab credited with no system ("an OpenAI model"): record that string, do not guess which model.
- Where the source calls it a pre-release, internal build or agent harness rather than a shipped model, say so; the name will not carry it.
- **"Claude" is a common given name among mathematicians** — Berge, Shannon, Chevalley, Viterbo, Jean-Claude Fournier — and other model names have ordinary meanings too. Confirm that a name in mathematical prose refers to a model.

Where a source discloses compute, tokens or money, record it in `disclosed_cost`.

---

## 6. Traps

**Priority and attribution disputes are common here.** Record them in `disputes` rather than picking a winner silently.

**Retractions and updates postdate the paper.** A preprint that claimed a proof in March may have been withdrawn in May. Check the arXiv version history and any comments.

**Two events on one problem are normal.** A bound moved by a model in July and a claimed exact solution by humans in November are two events, not one story to reconcile. Record both, fully and separately, including each one's AI involvement. Deciding which one the problem's status rests on is explicitly not your job, and the answer can change later if the second claim fails.

---

## 7. What to return

One JSON object for the one problem you were given. Write it to the output path the harness gives you; if it gave you none, print it alone as the last thing in your reply, with no prose around it.

**The record holds your findings and nothing else.** You do not echo the statement, field or parent back — the harness has them. You do not record who ran you, on what model, or when; the harness stamps that in the run's manifest. §7.1 lists what other passes cover.

**Never truncate it.** Not the summary, not the source list, not the search log. A partial record that looks complete is worse than an absent one, because nobody downstream can tell it was cut. If you could not finish, name what is missing in `incomplete`.

**Every answer carries the links that establish it.** That is what the per-item `sources` arrays are for: a reader must be able to see which URL supports the date, which supports the checking, and which supports the AI attribution. A single flat list at the bottom does not do that.

**Prose fields are not decoration.** Where a field asks what something was, a sentence that a stranger could act on is the deliverable. "A case of the conjecture" is not usable; "proves it for all abelian fourfolds over finite fields, leaving every other case open" is.

```jsonc
{
  "key": "jacobian-conjecture",        // exactly as given; the only input you echo

  "nothing_found": false,              // true when the search found no event at all; `events` is then []
  "outcome": "One sentence saying what has happened to this problem since 26 January 2024.",

  // ---- §5.1. Written once, about the problem, before you look at any event: every part of what
  // the statement demands, enumerated. Do not narrow it to fit what you found.
  "problem_asks": "Everything the statement asks for, part by part.",

  // Every event bearing on this problem, including ones you expect to be discounted. No ranking:
  // which event the problem's status rests on is decided by a later pass.
  "events": [{
    "id": "baek-2024-11",              // short slug, unique within this record
    "what_happened": "What was claimed or shown, by whom, and where it appeared.",

    "date": "2024-11-29",              // the FIRST public written argument (§5.1)
    "precision": "day",                // day | month | year
    "kind": "preprint",                // preprint | announcement | repository | journal | conference
    "predates_frozen_revision": false,
    "revisions": "v1 Nov 2024; v3 Mar 2026 repairs a gap in §4.",   // null if none found

    // ---- §5.1: this event against `problem_asks`. Two separate questions; do not merge them.
    "delivers": "What the result establishes, with the restrictions it carries.",
    "remains": "Which parts of `problem_asks` this event leaves open.",

    // ---- §5.2: who has worked through it. [] with no_engagement_found true is a real finding.
    "checked_by": [{
      "who": "Name of the person, journal or body",
      "qualification": "Why they are in a position to judge it",
      "what_they_did": "Worked through the proof / accepted it / published a verification",
      "where": "https://…",
      "automated": false               // true for review sites, AI referees, bundled audit reports
    }],
    "no_engagement_found": false,      // nobody has publicly engaged
    "time_since_posted": "14 months",  // where silence is the finding
    "machine_checked": null,           // {"system": "Lean 4", "sorry_free": true, "url": "…"}
    "directly_checkable": null,        // the object anyone can check by hand, and how

    // ---- §5.2: signals only. Do not deliver a verdict on whether it should count.
    "doubts": "Specific reasons for doubt, each with what it rests on. null where there are none.",
    "later_work_cites_it": null,       // true | false | null if not established
    "withdrawn": null,                 // {"what": "…", "date": "…", "by": "author|journal", "sources": […]}

    // ---- §5.3
    "direction": "Which way it cuts relative to what the problem asserts, in words.",
    "object": null,                    // the object exhibited: what it is, what it shows, and whether
                                       // it is explicit or non-constructive. Not whether it
                                       // contradicts the problem — that is the judging pass (§7.1).

    "people": ["Credited humans"],

    // ---- §5.4: systems credited with something that is in the result.
    "ai": {
      "none_found": false,             // true only where no system was involved at all, even peripherally
      "systems": [{
        "name": "…",                   // exactly as the source names it (§5.4)
        "what_it_did": "What this system produced, in the authors' words where possible",
        "basis_quote": "The authors' own sentence",
        "quote_url": "https://…"
      }],
      "disclosed_cost": null,          // where a source states compute, tokens or money
      "sources": ["…"]
    },

    "sources": ["…"]
  }],

  "disputes": [{"kind": "priority", "summary": "…", "sources": ["…"]}],

  // ---- the reasoning, which is the most valuable thing you produce
  "summary": "One paragraph: what was found and from which sources. Where a call was close, both readings.",
  "competing_reading": "The strongest case for reading the evidence differently.",
  "what_would_settle_it": "The evidence that would resolve the ambiguity.",
  "confidence": "high",                // high | medium | low — about your search, not about the mathematics

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

  "incomplete": null                   // what is missing, if anything; null when the record is whole
}
```

### 7.1 What other passes cover

Deliberately not your job. Researching them here would mean answering the same question hundreds of times:

| Fact | Why it is elsewhere |
|---|---|
| The year the problem was posed | Static, unrelated to what happened since 2024; one pass over all 457 |
| Whether the problem had its own Wikipedia article in January 2024 | A January 2024 fact about the encyclopedia, answerable in bulk |
| Each named system's lab and public release date | The same fact in every record naming it; researched once into a model table |
| Which problems imply which | Needs every record at once; a cross-pass after this one |
| How this problem is finally counted, and which event that rests on | The judging pass, from your record |
| Whether an exhibited object contradicts what the problem asserts | The judging pass, from `object` and `direction` (§5.3) |
| Who ran this, on what model and when | The harness records it |
| Dataset-wide counts and the audit | Aggregated from the records; you cannot see the others, so do not summarise the dataset |

If one of these looks obviously wrong in passing — a model credited that could not have existed at the date claimed, say — put it in `summary`. Do not research it.

---

## 8. Coverage and honesty

- **Do not silently narrow the work.** If you cannot research this problem to the standard above — a source you could not reach, a language you cannot read, a paywall — deliver the record with what you have, set `confidence` low, and say plainly what you could not do. A record that names its gap is usable; one that implies a completeness it does not have is not.
- **`low` confidence is a real answer.** On the previous run nobody ever used it, which made the field worthless. If your search left you genuinely unsure, say so.
- **Do not let time pressure lower the bar.** A fast pass that records no event without recording what was searched produces exactly the failure §4.1 exists to prevent: a denominator that looks complete and is empty.
- **One problem is the whole job.** There is no batch to get through and no quota to hit, so the pressure that makes a researcher skim does not apply. Spend the effort this problem needs.
