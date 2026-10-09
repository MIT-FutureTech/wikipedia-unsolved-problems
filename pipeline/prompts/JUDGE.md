# Judging instructions

You are given **one** research record: everything an earlier agent could find out about one mathematical problem and what has happened to it since January 2024. That agent was told not to classify any of it, and it did not. Your task is to read what it found and decide what the evidence actually establishes — how much of the problem has moved, whether anyone qualified has checked it, whether it should be believed at all, and whether an AI system did the mathematics. The problem is from Wikipedia's *List of unsolved problems in mathematics* (as it stood on 26 January 2024), and that statement, in its own words, is the question every answer below is about.

The project behind it asks: **of the mathematical progress made since early 2024, how much of it involved an AI system?** The research pass builds the denominator — all 457 problems on the frozen list, researched whether or not anything happened to them. **You are the numerator.** A problem is counted as moved, and counted as moved by a machine, because this pass said so and for no other reason.

**The record is evidence, not a draft to approve.** It carries no status, no codes and no verdict, so there is nothing in it to agree or disagree with. You are not re-doing the research either: the searching is done, the sources are open, the findings are written down. **Do not search the web, and do not open anything.** Judge the record in front of you and nothing else — if a tool is available to you here, that is the harness being permissive, not an invitation. A verdict that reaches past the record cannot be compared with the others or re-derived later, and a question the record cannot answer is a `doubts` entry, not an errand. Read them and answer the six questions in §2, for every event, one event at a time. You do not decide what the problem's status finally is: the harness works that out from your answers by the rules in §3, which is arithmetic and not a seventh question.

So the question in your mind is never *what did the researcher think?* It is **what does this evidence support?** Where two readings are close, set both down, choose one, and say what made the difference.

**Your decisions are final.** Nobody signs off on them and no pass comes after you. You never touch the original record — the harness builds the judged copy from your verdict (§5). So make each call as the last word on it, say plainly where you are unsure, and never soften a disagreement into agreement to avoid friction.

---

## 1. What you are given

- **The statement**: the problem exactly as the January 2024 list words it. This is your reference for the problem being investigated, and where this document says "the statement" it means this one.
- **The research record**: the research pass's JSON object, carrying research information but no classification codes or judgements.
- Possibly a `corrections` array from earlier human review. **Treat it as someone else's argument to evaluate, not as the answer.** If you think a correction was wrong, say so.

The fields each question leans on:

| Field | Feeds |
|---|---|
| `events[]`, each with `date`, `precision`, `kind`, `revisions`, `predates_frozen_revision` | Q1 |
| `problem_asks` (record-wide), and each event's `delivers` and `remains` | Q2 |
| `checked_by[]`, `no_engagement_found`, `time_since_posted`, `machine_checked`, `directly_checkable` | Q3 |
| `doubts`, `later_work_cites_it`, `withdrawn` | Q4 |
| `ai.none_found`, `ai.systems[]` | Q5 |
| `direction`, `object` | Q6 |
| `disputes` (record-wide) | Q4, and who the result is credited to |

If `nothing_found` is true, and `events` is empty, the researcher looked and found nothing. That is a finding, not a gap. Read `search` for what was run and satisfy yourself it was real; with no events to answer for, there is nothing else to do, and the harness records the problem as open.

`competing_reading` is the researcher's strongest case for reading the evidence differently, and `what_would_settle_it` names the evidence it could not get. Weigh both before you answer: a reading the researcher argued and rejected may still be the right one.

---

## 2. The questions

For every event in the record, we ask six questions. To reiterate, we aren't asking that of the problem statement, and not of the entire record. We want to determine these six questions for each of the events themselves, since a single problem might have had multiple events occur. An event that settles a case and an event that moves a bound get their own six answers. 

### Q1. What happened, and when?

The record's `events` array is that list, one entry per preprint, announcement, repository, formalisation or published paper bearing on this problem. Each carries a `date` — the **first public written argument**, not a journal date and not a revision date — with its `precision` and a `predates_frozen_revision` flag (indicating if the event happened before the January 2024 list). Check each date against `revisions` and `what_happened` rather than taking the flag on trust, and say for each whether it falls before or after 26 January 2024.

- A revision is not a new event unless the record shows it contains new mathematics. A 2022 preprint re-posted in 2025 with "minor changes" is a 2022 event; `revisions` is where the record says which it is.
- A year-only date of 2024 cannot be placed either side of 26 January. Answer `after_snapshot` null; do not guess. Null is for a date that cannot be placed, not for one you are unsure of.
- The array is the researcher's division of the evidence, not gospel. Two entries describing one event, or one entry bundling two, both happen: work from what the evidence shows and say so.

### Q2. Scope — how much of *this problem* does the event settle?

| Answer | Means |
|---|---|
| `whole` | Answers the question the statement asks, **all of it**: every part, every constant, every conjecture it names |
| `case` | Settles a **restriction** of the question: a dimension or range, a class of objects, one named part of a multi-part statement, one of several listed conjectures or constants |
| `bound` | Moves a quantity on a question that stays open: an upper or lower bound, a record construction, the smallest known counterexample dimension, a proportion, an exponent |
| `instances` | Checks finitely many instances of a universal statement: a search to N, a census up to size n, certificates for sampled cases. **This does not count as  movement on the problem.** |
| `variant` | Settles a **changed** question: an analogue, different hypotheses, a stronger or weaker form, a different problem sharing a name. **This does not count as movement on the problem** |
| `none` | Bears on the problem without settling or bounding anything: a reduction to an unproven condition, a survey, a formalisation of known results, a research programme proposing a route to a proof, or a benchmark |

`problem_asks`, `delivers` and `remains` are the researcher's attempt to summarise what it found: what the problem wants, what this event gives, what is left over. That is raw material for this question, not an answer to it — the researcher was told to make the gap visible and explicitly not to measure it. Read `problem_asks` against the statement yourself before you use it, because a paraphrase that quietly narrows the question turns a `case` into a `whole` (F6).

Test for `whole` against the statement's own words. If the statement names two conjectures, a proof of one is a `case`. If it lists fourteen constants, one constant is a `case`. If it asks for the value of a quantity, a better bound is a `bound`. But if it asks only whether something *below* a threshold exists, reaching below the threshold answers it: the statement "universal point sets of subquadratic size" is answered in full by an n^(1+o(1)) construction, even though the true order stays open. The statement's wording decides, not the problem's wider literature.

A record counts as `whole` only where the record *is* the question — the statement asks for a specific value, and the value is determined.

### Q3. Verification — has anyone qualified checked it?

| Answer | Means |
|---|---|
| `digested` | A **named** human expert worked through the argument and said so in public, or a journal of record accepted it, or named experts published a verification or a digested rewrite |
| `checkable` | The result is an explicit object anyone can check directly by hand or by computer algebra — a polynomial map, a graph, a configuration — and the check is simple enough to be decisive |
| `unreviewed` | Anything else: a preprint however prestigious the author, an announcement, a machine proof whose only reader is the compiler, an automated review |

**An entry in `checked_by` is not itself digestion.** That array collects everyone who engaged with the result, and engagement is a much lower bar than this one. Read the entry's `qualification` and `what_they_did`, not the fact that it exists: `digested` needs someone placed to judge *this* argument who went through it — worked the proof, published a verification or a digested rewrite, accepted it for a journal of record, approved the thesis containing it. Someone who cited it, mentioned it approvingly, called it important, or posted that it looks right has engaged with it and not read it, and that entry leaves the event `unreviewed`.

The bar is what one person did, not how many did it. A single named expert who worked through the argument can be digestion if thorough or noteworthy; ten people repeating the announcement are not. Being conservative here is its own error — see F9.

The rest reads off the record directly: `directly_checkable` filled in is `checkable`; `machine_checked` on its own, or `no_engagement_found` true, is `unreviewed`. Where `checked_by` is empty, `time_since_posted` says how long the silence has lasted, which Q4 needs.

**Automated review sites and AI referees are not experts** (Pith Review, Refine, a lab's own "adversarial review panel", a repository's bundled audit report). **A clean Lean build is not digestion** — see failure mode F7. **Informal expert reading counts if it is named and public**: a blog post, a SIAM News essay, a guest post saying "yes, the proof is correct", a doctoral committee approving the thesis that contains it.

### Q4. Credibility — should this event count at all?

| Answer | Means |
|---|---|
| `credible` | No specific reason for doubt beyond the absence of review |
| `doubtful` | Real reasons for doubt, not enough to set it aside. **Keep it**, and name the doubt |
| `not_credible` | Set aside: the signals in F10 are present together, strongly enough that counting it would put noise in the numbers |
| `knocked_down` | Set aside: withdrawn, retracted, conceded, or carrying a specific identified error in a key step that nobody has answered |

`doubts` holds the specific reasons the researcher found and nothing where it found none — an empty `doubts` is itself a finding, and on its own it means `credible`. `withdrawn` records a retraction or concession, and `later_work_cites_it` false on a claimed landmark is the same silence F10 describes.

`not_credible` is a strong call and needs several signals at once — at minimum, no expert uptake over a period long enough to expect some, on a problem where a resolution would be a landmark, and ideally one of: the author is outside or at the margin of the field; papers on the same question after the claim still call it open and do not cite it; the claim's own history (scope ballooning, many patch revisions, a hedged title, a predatory venue); the method is one the problem is known to resist. Absence of review alone is **never** enough — that is what `unreviewed` is for.

`knocked_down` needs a specific error, not a vague objection: "the quantity the proof needs to be negative is numerically positive" knocks a claim down; "an automated reviewer flagged a notation issue" does not.

### Q5. AI role — who did the mathematics in *this event*?

| Answer | Means |
|---|---|
| `generated` | By the authors' own account, an AI system produced the proof, the construction or the bound, and people checked it |
| `assisted` | Human-led work in which, by the authors' own account, an AI system produced **part of the mathematics that is in the result** — an argument, a construction, a case |
| `none` | No AI, **or** the AI only checked, proofread, debugged, searched literature, suggested strategies, formalised, drafted prose, or **criticised** the work |

Judge from the `basis_quote` on each entry in the event's `ai.systems`, and ask one question: *what did the model produce that is in the final result?* The word the source uses ("assisted", "with the help of") is not the code.

A system whose involvement stopped at checking a proof, proofreading, debugging code, searching the literature or formalising an argument already proved never reaches `ai.systems` at all: the research pass records what it did in `summary` instead, and leaves `none_found` false. So `none_found` false with an empty `systems` means a system was involved but did none of the mathematics: that is `none`, and it is a different finding from no system at all.

A model that suggested a strategy, drafted the prose or **criticised** the work can arrive in `ai.systems` with a quote attached, because the research pass was told to record it and let you weigh it. Weigh it: an AI arguing that human work is wrong did not produce it (F12), but a strategy the humans then had to prove *is* mathematics the system supplied. Inclusion is a claim you check against the quote, never a verdict you inherit, and if the model contribution is thin based on the quote, it is `none`, regardless of how prominently the system is named.

Where one event credits several systems, its role is the strongest any of them earned.

**Answer this for the event in front of you, and only that event.** The role is a property of the event, never of the problem: a model credited in one paper earns nothing for a second paper that happens to be about the same problem (F13). You do not need to know which event will end up carrying the problem's status — answer each from its own quote and §3 step 4 makes sure a credited model is not dropped by the arithmetic.

### Q6. Direction and counterexample

- **The object**, where the event exhibited one. The record's `object` is one piece of prose saying what it is, what it shows, and whether it is explicit or came from a non-constructive existence proof. **The research pass does not say what the object does to the problem — deciding that is this question**, because it turns on what the statement asserts rather than on anything about the object itself. Three answers:
  - `counterexample` — it contradicts what the statement asserts.
  - `witness` — it is what the statement asked for. An object answering an existence question affirmatively settles the question and contradicts nothing.
  - `null` — the event exhibited no object, or none that bears on the statement either way.

  Producing an object is a different achievement from proving a statement about infinitely many cases, so a witness is recorded as such and not flattened into "no counterexample".
- **Direction** of the event: `refuted` (goes against the conjecture), `confirmed` (proves what was conjectured, or answers as expected), `mixed` (settled cases went both ways), or `null`. The record's own `direction` is prose written before anyone weighed the scope: evidence for this answer, but the final answer is your judgement call.
- A `counterexample` is never `confirmed`; a `witness` usually is, since the statement asked for the thing that was found. A `bound`, `instances`, `variant` or `none` has direction `null`.

---

## 3. What the harness does with your answers

**You do not do any of this.** It is set down so you can see what each answer controls, because an answer whose consequence you cannot see is one you cannot give carefully. Every step below is arithmetic over the rows you return in §5.

**Step 1 — discard.** Every event answered `not_credible`, `knocked_down`, `variant`, `instances` or `none` is set aside. It stays in the record as evidence, and it cannot set the status. This is the step that makes a `variant` answer consequential: it removes the event from the running entirely.

**Step 2 — tier.** Each remaining event gets a tier from the two answers that decide it:

| Scope | Verification | Tier |
|---|---|---|
| `whole` | `digested` or `checkable` | `resolved` |
| `whole` | `unreviewed` | `claimed` |
| `case` | any | `partial` |
| `bound` | any | `progress` |

**Step 3 — the furthest event wins.** The status is the highest tier among the events you marked as falling after the snapshot: `resolved` > `claimed` > `partial` > `progress`. That event is **the event the status rests on**: its `direction` and `object_role` become the problem's, and its date, sources and credited people are taken from the record. Where several events tie at the top tier, the earliest of them is the one it rests on — that is when the problem moved.

This ordering is why a later human proof buries an earlier AI bound on the same quantity (moving sofa). The bound is not a lesser result that still counts a little; it is a dead one, and you do not need to say so — answering `bound` for it and `whole` for the proof is enough.

**Step 4 — same tier, AI counts if any of it was AI.** Where several events share the top tier (two different bounds moved, two different cases settled), the problem's `ai_role` is the strongest among them, whichever of them step 3 rested on. So AI credit is never lost to a tiebreak: answer each event's role from its own quote and the arithmetic will not drop it.

**Step 5 — nothing left.** If no event after the snapshot survives, the problem is `open_stale` where some event *before* the snapshot tiers as `resolved`, and `open` otherwise. A pre-snapshot partial result or claim is a note on a problem still open, not `open_stale`. This is why pre-snapshot events get the full six answers like any other: the difference between `open` and `open_stale` is computed from them. An event whose date you answered null counts in neither step 3 nor this one; it stays in the record with its answers.

**Step 6 — direction.** `resolved`, `claimed` and `partial` carry the direction of the event the status rests on. `progress`, `open` and `open_stale` carry `null`, whatever you answered for the individual events.

None of this is a second opinion, and none of it is yours to perform. The record holds no codes to overturn and you produce none: you answer six questions per event, the steps above turn those answers into the problem's status, and that status goes straight into the dataset. Answer the events and let the arithmetic happen.

---

## 4. Failure modes

Every one of these happened on the first run. They are grouped by the answer each one corrupts, because that is when you will need them: the arithmetic in §3 is only as good as the rows you hand it. They name no problems — the record in front of you is the only evidence about it.

### Q1 — dates

**F1. A revision re-dates old work.** The date is the first public written argument, not the latest version carrying it, and whether the event falls after the snapshot can turn on that alone. A preprint re-posted years later with "minor changes" keeps its original date. Move it only where `revisions` shows new mathematics in the later version.

### Q2 — scope

**F2. Scope and verification answered as one question.** The commonest error on the first run, and the reason this pass exists. "An unreviewed special case" is two answers, not one: `case` for Q2, `unreviewed` for Q3. They are separate fields in your row and §3 step 2 is what combines them. Never let one pull the other.

**F3. A multi-part statement read as one question.** Count what the statement names before answering it. Where it names several conjectures, or several constants, or asks two questions in one sentence, settling one of them is `case`.

**F4. A moved quantity read as a determined one.** Improving a bound leaves the quantity unknown: `bound`, not `whole`. This holds even when the improvement is dramatic, and even when it is the first in decades. A refutation already on the record is the same trap — a counterexample in a new dimension, for a conjecture known to fail somewhere already, moves the frontier rather than settling anything.

The case worth stating twice: a theorem about how far a proof *method* can reach bounds the method and not the problem, so it scores `none` — unless the same theorem also moves the problem's own quantity, and then it is a `bound` like any other.

**F5. Finitely many instances read as progress.** No finite check touches a statement about infinitely many objects: a verification to some height, a census up to some size, certificates for a sample. They narrow where a counterexample could hide and settle nothing. Answer `instances`, which §3 step 1 discards.

**F6. The record's paraphrase trusted over the statement.** `problem_asks` is the researcher's summary, written by someone who had already found the result. A summary that quietly narrows the question turns a `case` into a `whole`. Answer against the statement you were given; where the two diverge and the record cannot settle it, answer on the statement and say so in `doubts`.

### Q3 — verification

**F7. A formal check read as a reading.** A zero-`sorry` build proves the formal statement, not that the formal statement is the conjecture. The gap between them is where the risk lives: a quantifier in the wrong order, a hypothesis dropped, a definition quietly weaker than the field's standard one. No kernel catches any of that, and kernels have had soundness bugs of their own. A result resting only on a formal check is `unreviewed`.

**F8. Automated review read as a verdict.** A review site, an AI referee, a lab's own adversarial panel, a bundled audit report: none is digestion and none is a knock-down. At most they say where a human should look.

**F9. Digestion held to too high a bar.** `digested` does not require a journal. A named expert working through the argument in public clears it, whether that appears as a paper, a blog post, a seminar write-up or a thesis a committee approved. The first run was too strict here, and strictness is as wrong as looseness, in the other direction.

### Q4 — credibility

**F10. Absence of review treated as a reason for doubt.** That is what `unreviewed` already records, and it is the normal state of recent work. `not_credible` needs several of these at once: no uptake on a problem where a resolution would be news; later papers on the very same quantity still calling it open; an author far outside the field attempting something the field considers out of reach; a history that undermines the claim, such as scope ballooning between versions, a long dormancy followed by many rapid revisions, a hedged title, or a venue that reviews nothing. An established researcher with a serious method and no identified error is `doubtful` at worst.

**F11. An unanswered error treated as a quibble.** `knocked_down` needs something specific in a key step that nobody has answered — a quantity the proof needs to be negative shown to be positive, say — not a general objection. A withdrawal, retraction or concession counts the same. Both leave the problem exactly where it was.

### Q5 — AI role

**F12. The word in the source read as the answer.** Ask only what the model produced that is in the result. "Helped check the construction" is checking, which is `none`, whatever the surrounding sentence calls it. A system that found gaps in human work criticised it rather than producing it: `none`. A disclosure naming a coding assistant for the verification scripts and a chatbot for the prose credits neither with mathematics. A phrase like "the findings grew out of research at an AI lab" does not say who found what, so it supports nothing. And "computer-assisted" is usually not AI at all: SAT solvers, computer algebra, exhaustive search, interval arithmetic.

**F13. Credit carried in from another event.** Each row is answered from its own event's quote. A model that moved a bound one month, and a human proof that settled the problem outright some months later, are two rows: the model earns `generated` in its own and nothing in the other. Credit does not travel between events because they concern the same problem.

### Q6 — direction

**F14. A witness read as a counterexample, or flattened away.** Two errors with one cause: not asking what the statement asserts. An object that answers an existence question affirmatively is what was asked for, so it is a `witness`, never a `counterexample` — and it is never `null` either, because an object was exhibited and that is worth recording. A counterexample contradicts the statement and is never `confirmed`. An event that settles nothing takes direction `null`.

### The record itself

**F15. The record may be about a different problem.** Some entries on the list link a background topic, a related theorem or a namesake's biography instead of the problem, and a record built on the linked article answers the wrong question. Model names are ordinary words and given names too: Claude Berge, Claude Shannon and Claude Chevalley are not models.

**F16. The record may have nothing behind it.** Some first-run records were written with web search silently broken. The record shows it: empty `search.queries`, sources with `opened` false, a filled-in `incomplete`. Where there is no real search, or the central claim rests only on unopened snippets, do not judge the claim — set `insufficient_evidence` true and say in `doubts` what is missing.

---

## 5. What to return

**Your answers, one row per event.** You return no status, no AI role for the problem and no direction for the problem: those are the harness's, computed from these rows by §3. What you return is the six answers for each event in the record, and the reasoning behind them. Write the verdict to the path the harness gives you and write no other file.

**You do not retype the record.** Refer to each event by the `id` the record gives it. The date, the sources and the credited people are taken from the record itself, so every fact that reaches the dataset is one the researcher found and you did not re-key.

```jsonc
{
  "key": "jacobian-conjecture",        // exactly as the record gives it

  // One row per event in the record, in the record's order. Every event gets a row, including ones
  // §3 step 1 will discard and ones before the snapshot — the discards are what makes the result
  // auditable, and the pre-snapshot rows are what separate `open` from `open_stale`.
  "events": [{
    "id": "broe-2026",                 // the record's own event id, copied
    "after_snapshot": true,            // true | false | null — your reading of the date (Q1), not the
                                       // record's flag; null only where the date cannot be placed
    "scope": "case",                   // whole | case | bound | instances | variant | none
    "verification": "unreviewed",      // digested | checkable | unreviewed
    "credibility": "credible",         // credible | doubtful | not_credible | knocked_down
    "credibility_reason": null,        // required unless credible
    "ai_role": "none",                 // generated | assisted | none — for THIS event, from its own quote
    "ai_basis": null,                  // the systems[] quote you relied on, where not none
    "ai_systems_credited": [],         // names from this event's ai.systems, exactly as recorded
    "direction": "confirmed",          // refuted | confirmed | mixed | null
    "object_role": null                // counterexample | witness | null — your call on this event's
                                       // `object` against the statement (Q6)
  }],

  "why": "One paragraph: how you answered the events that matter and what made the close calls go the way they did. Not which event wins — that is not your question.",
  "doubts": "Anything a later reader should know that none of the answers above carries. null where none.",
  "insufficient_evidence": false,      // true where the record could not be judged (F16)
  "confidence": "high"                 // high | medium | low — about your answers, not the mathematics (below)
}
```

**Never add a fact that is not in front of you.** Every name, date, identifier and source in your verdict must appear in the record or in a page you opened in this run. Where the record gives only surnames, give only surnames; where it gives only a month, give only the month. A gap is honest; a plausible first name is fabrication.

**Never discard evidence.** An event that §3 step 1 will set aside still gets its row, carrying the answer that sets it aside. Where you doubt a quote the researcher relied on, say so in `doubts` and answer on what the quote supports — the quote stays in the record either way, and nothing you return removes anything from it.

**`confidence` says how firmly the record supports your answers.** `high`: every answer follows from what the record says. `medium`: at least one answer was a close call, and `doubts` names it. `low`: an answer depends on something the record does not say. `medium` is not a default: if you cannot name the close call, it is `high`.

### Before you return, check

1. Every event in the record has a row, including the discards and anything before the snapshot.
2. No row names an event the record does not have.
3. Each row's `ai_role` was answered from that event's own quote, not from what another event did.
4. A `whole` scope survives a re-read of the statement's exact wording.
5. `not_credible` has several F10 signals, not just an absence of review, and carries its reason.
6. You assigned no status, and picked no winning event. If you found yourself doing either, the answers you were deriving it from are the ones to check.
7. You wrote the verdict file and nothing else.
