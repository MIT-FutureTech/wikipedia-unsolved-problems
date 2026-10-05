# Judging instructions

Pass three. You are given **one** research record about one problem from Wikipedia's *List of
unsolved problems in mathematics* as it stood on **26 January 2024**, written by an earlier agent
that searched the literature. Your job is to **judge** it: decide what the evidence in the record
actually establishes, and correct the record where its codes do not follow from its own evidence.

You are not re-doing the research. The researcher already searched, opened sources and wrote down
what it found. What it got wrong, repeatedly, was the classification — and nearly always the
record's own summary contained the facts that should have changed the code. Read the record as
evidence, answer the questions in §3, and let the codes follow from your answers by the table in §4.

**Your decisions are final, and they go in a separate file.** You do not ask for approval and
nobody signs off on your calls. You never edit the original record: your verdict (§7) is applied to a
separate copy of it. So make each call as
the last word on it, say plainly when you are unsure, and never soften a disagreement into
agreement to avoid friction.

One record, one verdict, one run. Read this whole document first.

---

## 1. What this measures, and why judgement is its own pass

On review, about half of the problems the research first coded as resolved or claimed did not hold
up: some were claims no expert had taken up, several had already been knocked down, and most were
special cases or bounds filed as if they were full resolutions. None of that was a search failure.
The researcher found the right papers and described them accurately, then chose the wrong code,
because its instructions asked one field to answer two questions at once — *how much of the problem
was settled* and *has an expert checked it*. This pass asks those questions separately.

---

## 2. What you are given

- **The bullet**: the problem statement exactly as the January 2024 list gives it. This is the
  question. Not the problem's Wikipedia article, not the "famous" version, not the official prize
  statement unless the bullet points to it.
- **The record**: the researcher's JSON — `summary`, `outcome`, `event`, `competing_reading`,
  `ai.basis_quote`, `disputes`, `sources`, `search`, and the current codes (`status`, `ai_role`,
  `resolution_direction`, `counterexample`).
- Possibly a `corrections` array from earlier human review. **Treat it as someone else's argument
  to evaluate, not as the answer.** If you think a correction was wrong, say so.

The `competing_reading` field is where the researcher put its doubts. Read it closely: in most of
the records later corrected, the correct answer was sitting there, argued and then rejected.

---

## 3. The questions

Answer every question for every event in the record, then pick the event the status rests on.

### Q1. What happened, and when?

List every distinct **event** the record describes: each preprint, announcement, repository,
formalisation or published paper that bears on this bullet. For each give the date of the **first
public written argument** (not a journal date, not a revision date), its precision, and whether it
falls before or after 26 January 2024.

- A revision is not a new event unless the record shows it contains new mathematics. A 2022
  preprint re-posted in 2025 with "minor changes" is a 2022 event.
- A year-only date of 2024 cannot be placed either side of 26 January. Say so; do not guess.

### Q2. Scope — how much of *this bullet* does the event settle?

| Answer | Means |
|---|---|
| `whole` | Answers the question the bullet asks, **all of it**: every part, every constant, every conjecture it names |
| `case` | Settles a **restriction** of the question: a dimension or range, a class of objects, one named part of a multi-part bullet, one of several listed conjectures or constants |
| `bound` | Moves a quantity on a question that stays open: an upper or lower bound, a record construction, the smallest known counterexample dimension, a proportion, an exponent |
| `instances` | Checks finitely many instances of a universal statement: a search to N, a census up to size n, certificates for sampled cases. **Not movement** |
| `variant` | Settles a **changed** question: an analogue, different hypotheses, a stronger or weaker form, a different problem sharing a name. **Not movement on this bullet** |
| `none` | Bears on the problem without settling or bounding anything: a reduction to an unproven condition, a survey, a formalisation of known results, a programme or a benchmark |

Test for `whole` against the bullet's own words. If the bullet names two conjectures, a proof of one
is a `case`. If it lists fourteen constants, one constant is a `case`. If it asks for the value of a
quantity, a better bound is a `bound`. But if it asks only whether something *below* a threshold
exists, reaching below the threshold answers it: the bullet "universal point sets of subquadratic
size" is answered in full by an n^(1+o(1)) construction, even though the true order stays open.
The bullet's wording decides, not the problem's wider literature.

A record counts as `whole` only where the record *is* the question — the bullet asks for a specific
value, and the value is determined.

### Q3. Verification — has anyone qualified checked it?

| Answer | Means |
|---|---|
| `digested` | A **named** human expert worked through the argument and said so in public, or a journal of record accepted it, or named experts published a verification or a digested rewrite |
| `checkable` | The result is an explicit object anyone can check directly by hand or by computer algebra — a polynomial map, a graph, a configuration — and the check is simple enough to be decisive |
| `unreviewed` | Anything else: a preprint however prestigious the author, an announcement, a machine proof whose only reader is the compiler, an automated review |

**Automated review sites and AI referees are not experts** (Pith Review, Refine, a lab's own
"adversarial review panel", a repository's bundled audit report). **A clean Lean build is not
digestion** — see failure mode F10. **Informal expert reading counts if it is named and public**: a
blog post, a SIAM News essay, a guest post saying "yes, the proof is correct", a doctoral committee
approving the thesis that contains it. Look for these; researchers under-credited them.

### Q4. Credibility — should this event count at all?

| Answer | Means |
|---|---|
| `credible` | No specific reason for doubt beyond the absence of review |
| `doubtful` | Real reasons for doubt, not enough to set it aside. **Keep it**, and name the doubt |
| `not_credible` | Set aside: the signals in F5 are present together, strongly enough that counting it would put noise in the numbers |
| `knocked_down` | Set aside: withdrawn, retracted, conceded, or carrying a specific identified error in a key step that nobody has answered |

`not_credible` is a strong call and needs several signals at once — at minimum, no expert uptake
over a period long enough to expect some, on a problem where a resolution would be a landmark, plus
at least one of: the author is outside or at the margin of the field; papers on the same question
after the claim still call it open and do not cite it; the claim's own history (scope ballooning,
many patch revisions, a hedged title, a predatory venue); the method is one the problem is known to
resist. Absence of review alone is **never** enough — that is what `unreviewed` is for.

`knocked_down` needs a specific error, not a vague objection: "the quantity the proof needs to be
negative is numerically positive" knocks a claim down; "an automated reviewer flagged a notation
issue" does not.

### Q5. AI role — who did the mathematics in *this event*?

| Answer | Means |
|---|---|
| `generated` | By the authors' own account, an AI system produced the proof, the construction or the bound, and people checked it |
| `assisted` | Human-led work in which, by the authors' own account, an AI system produced **part of the mathematics that is in the result** — an argument, a construction, a case |
| `none` | No AI, **or** the AI only checked, proofread, debugged, searched literature, suggested strategies, formalised, drafted prose, or **criticised** the work |

Judge from `ai.basis_quote` and ask one question: *what did the model produce that is in the final
result?* The word the source uses ("assisted", "with the help of") is not the code.

The AI role belongs to the event the status rests on, not to the problem. If the status rests on a
human paper, the row is `none` even if a different paper about the same problem used a model — see
F8.

### Q6. Direction and counterexample

- **Counterexample**: is the event an explicit object that contradicts what the bullet asserts? An
  object answering an existence question affirmatively is a *witness*, not a counterexample.
- **Direction** of the event: `refuted` (goes against the conjecture), `confirmed` (proves what was
  conjectured, or answers as expected), `mixed` (settled cases went both ways), or `null`.
- A counterexample is never `confirmed`. A `bound`, `instances`, `variant` or `none` has direction
  `null`.

---

## 4. From answers to codes

**Step 1 — discard.** Set aside every event that is `not_credible`, `knocked_down`, `variant`,
`instances` or `none`. They stay in the record as evidence; they cannot set the status.

**Step 2 — tier.** Give each remaining event a tier:

| Scope | Verification | Tier |
|---|---|---|
| `whole` | `digested` or `checkable` | `resolved` |
| `whole` | `unreviewed` | `claimed` |
| `case` | any | `partial` |
| `bound` | any | `progress` |

**Step 3 — the furthest event wins.** The status is the highest tier among remaining events after
the snapshot: `resolved` > `claimed` > `partial` > `progress`. That event is **the event the status
rests on**, and `ai_role`, `resolution_direction`, `counterexample` and `credited_humans` all
describe it. A later human proof supersedes an earlier AI bound on the same quantity (moving sofa):
the bound is not a lesser result but a dead one.

**Step 4 — same tier, AI counts if any of it was AI.** Where two events share the top tier and
neither supersedes the other (two different bounds moved, two different cases settled), the
`ai_role` is the stronger of their roles.

**Step 5 — nothing left.** If no event survives: `open_stale` if the record shows the problem was
**resolved** before 26 January 2024; otherwise `open`. A pre-snapshot partial result or a
pre-snapshot claim is a note on a problem still open, not `open_stale`.

**Step 6 — direction.** `resolved`, `claimed` and `partial` carry the direction of the chosen event.
`progress`, `open` and `open_stale` carry `null`.

If your derived codes differ from the record's current codes, list the change in your verdict with
a correction entry (§7). If they match, say so — agreement is a finding too.

---

## 5. Failure modes

Every one of these happened in this dataset. Most were caught by a human reading the record's own
summary. Check each one against every record.

**F1. Scope and verification conflated.** The commonest error by far. The researcher saw an
unreviewed result and coded it `claimed` — "a case settlement without expert digestion is
`claimed`" — so an unreviewed special case was counted as a resolution and shown as "Proved
(claimed)". The Birch and Swinnerton-Dyer conjecture (infinite families of curves), the Tate
conjecture (abelian fourfolds), Cartan–Hadamard (dimensions 3–9), Tuza (maximum degree 7), Ryser
(one case), the big-line-big-clique conjecture (one case) and the Hermite constants (one dimension)
were all coded this way. Q2 and Q3 are separate questions: answer them separately.

**F2. Multi-part bullets read as one question.** A bullet naming "the Hopf conjectures" covers the
product form and the sign form; refuting one is a `case`. The same happened with a bullet bundling
the Arnold and Arnold–Givental conjectures, a two-question bullet on monadic theories, the broad
"Arthur's conjectures", fourteen constants of which one was addressed, and "the rendezvous problem"
whose Anderson–Weber sub-conjecture was settled. Read the bullet and count its parts.

**F3. Bounds read as resolutions — and the reverse.** A lower upper bound on a constant does not determine it
(de Bruijn–Newman). A new record table entry does not settle a table (degree–diameter). A
counterexample in dimension 63 does not refute a conjecture already refuted in 1993 — it moves the
smallest known dimension (Borsuk). A theorem about how far a proof *method* can reach is a bound on
the method, not on the problem — unless it also improves the bound on the problem's own quantity,
as Astra's Cohn–Elkies result did for the sphere-packing upper-bound exponent, the first improvement
since 1978; then it is a `bound` like any other. The
reverse error happened too: a human reviewer recoded universal point sets from `claimed` to
`progress` by reading the problem as "close the linear–quadratic gap", when the bullet asks only
for sets of *subquadratic* size, which the claimed n^(1+o(1)) construction supplies. Read the
bullet's words before calling anything a bound.

**F4. Instances of a universal claim read as progress.** Verifying the Collatz conjecture to 2^71,
a census of all posets up to 14 elements, and periodicity certificates for 205 sampled cubics are
each finitely many examples of a statement about infinitely many objects. They narrow where a
counterexample could hide; they settle nothing. Scope `instances`.

**F5. A non-credible claim counted because the rule said "undigested preprint = claimed".** The
literal rule made every preprint count. The claims later set aside shared signals:

- *No uptake on a landmark problem*: a claimed proof of Montgomery's pair correlation conjecture
  (full range, even under RH, is far beyond known methods) sat ten months uncited; the live
  Wikipedia article covered adjacent work and not this.
- *Same-topic silence*: two later papers bounding exactly the eigenvalue in Yau's conjecture still
  called it open and did not mention a claimed full proof. That is as close to a knock-down as
  silence gets.
- *Author outside the field on a hard problem*: a physics student's claimed closed form for g(k)
  in Waring's problem needs control of (3/2)^k for every k, which is Mahler-problem territory.
- *The claim's own history*: a 2015 preprint dormant for a decade and then revised nine times in
  2025, presented by its author as "a posible proof" (Chern's conjecture); a scope jump from
  "r ≤ 26" to "all r" in twelve days (Albertson); a predatory venue (Whitehead); a decade-old
  dispute restated rather than advanced, which the relevant experts reject (abc, Joshi on IUT).
- *Misreading what is claimed*: the Chern record called "flat affine manifolds" a sub-case, but an
  affine manifold is flat by definition — it was the whole conjecture.

Conversely, **do not over-apply this.** An established researcher in the area, a serious method,
active revision and no identified error make a claim `doubtful` at worst (Casas-Alvero, Büchi's
problem), not `not_credible`.

**F6. A knocked-down claim kept.** Sun's proof that Catalan's constant is irrational stayed
`claimed` after Wachs showed the key inequality fails numerically and a partial Lean formalisation
agreed. A claim with a specific, unanswered error in its key step does not count, whether or not
its author has withdrawn it. Withdrawn claims (a Lean "disproof" of Collatz, a conceded
covering-system claim, a Siegel-zero preprint resting on a misreading) are the same: they leave the
problem where it was.

**F7. Old work re-dated by a revision.** A 2022 preprint whose 2025 v2 says "minor changes"
(Littlewood), a 2023 preprint revised in 2024 (Whitehead), and a 2023 result whose record admitted
it might only be fully established in a later version (Novikov). Date the first written argument;
a revision moves the date only if the record shows new mathematics in it.

**F8. The wrong event chosen, or the AI role taken from a different event.** The moving sofa's AI
credit came from a 2024 neural-network bound; its status rested on Baek's human proof four months
later. The 1/3–2/3 conjecture's AI credit came from a computational census, while the genuine
advance was Aires–Kahn's human bounds. Where a record describes several events, the status and the
AI role must describe the same one. Researchers also chose a more *eventful* item over a more
*genuine* one — a withdrawn self-published claim over a real advance described in the same record
(the inscribed square problem).

**F9. AI role errors.**
- *Word-matching*: the Carathéodory authors said Claude "helped check the construction" and the
  row was coded `assisted`. Checking is `none`.
- *AI as critic*: Refine found gaps in the human Hopf preprint; the row was coded as AI
  involvement. An AI arguing that human work is wrong did not produce it: `none`.
- *Named is not credited*: a paper disclosing GitHub Copilot for verification code and ChatGPT for
  exposition names systems but credits none of them with mathematics.
- *Thin quotes*: "the findings grew out of research at an AI lab" (Hadamard's determinant problem)
  does not say who found what. Code on what the quote supports and flag it.
- *"Computer-assisted" is not AI*: SAT solvers, computer algebra, exhaustive search and interval
  arithmetic are not AI systems.

**F10. Machine-checked is not the same as correct.** A zero-`sorry` Lean build shows the proof
proves *its formal statement*. It does not show the formal statement is the conjecture. The main
risk for an AI proof against a formalised benchmark is a mistranslated hypothesis — a quantifier
order, a missing degree condition, a home-made definition of φ-mixing weaker than the probabilists'
one — which no kernel can catch (the Smale mean value and Ibragimov–Iosifescu disproofs, neither
read by a human analyst). Proof assistants have also had soundness bugs: a Lean "disproof" of
Collatz exposed two, and an automated verifier passed a covering-system formalisation 7 of 7 checks
while it contained a provably false axiom. Where a result rests only on a formal check, Q3 is
`unreviewed`, and the doubt goes in your verdict.

**F11. Automated review read as either verification or refutation.** A Pith Review summary is
neither digestion nor a knock-down. It can point to where a human should look.

**F12. Expert digestion under-credited.** Researchers were conservative about `resolved` and
sometimes missed named expert reading that meets the bar: Crouzeix himself and two numerical
analysts read and endorsed one proof of Crouzeix's conjecture; a human-checkable case analysis
confirmed a Jaeger counterexample; a hand proof backs an explicit word-representability
counterexample; a doctoral thesis contains the Borel monadic theory result. Upgrades are
corrections too.

**F13. The problem statement misread.** The Navier–Stokes record called the forced equations "a
related but not identical problem" to the Clay statement, but the Clay breakdown alternatives (C)
and (D) explicitly allow a smooth forcing term under stated decay conditions — whether the claimed
counterexample meets those conditions is the question, and the record never asked it. Check a
record's paraphrase of the problem against the bullet, and against the official statement where the
bullet names one.

**F14. Direction and counterexample errors.** An exhibited counterexample coded `confirmed`
(Borsuk, originally); a witness to an existence question marked as a counterexample
(beggar-my-neighbour); `confirmed` on a `progress` row, where nothing was settled.

**F15. The wrong problem researched.** Some bullets link a background topic, a related theorem or
a namesake's biography rather than the problem. A record built on the linked article instead of the
problem's own name may be answering a different question. Model names are also ordinary words and
given names: Claude Berge, Claude Shannon and Claude Chevalley are not models.

**F16. Evidence too thin to judge.** Some records were written with web search silently broken:
no queries, no sources opened, and a status of "possible". If the record shows no real search
behind it, or its central claim rests only on unopened snippets, do not judge the claim — leave
its codes as they are, set `insufficient_evidence` true, and say in `doubts` what is missing.

---

## 6. When you may search

You have web search and fetch. **Use them sparingly and only for these:**

1. **Has anything happened since the record was written?** For an event you would code
   `claimed`, `doubtful` or `not_credible`: has it been withdrawn, rebutted, digested or accepted
   since the record's check date? One or two searches.
2. **Does a digestion the record hints at exist?** For F12: find the named expert's post or the
   acceptance notice.
3. **Is the claimed statement the stated problem?** For F10 and F13, where the record gives a link
   to the formal statement or the official problem, open it and compare.

Do not re-research the problem. Do not look for new events the researcher missed; that is a
different pass, and a verdict that quietly adds events cannot be compared with the rest. Five
searches is a lot for one record. Record every query verbatim.

---

## 7. What to return

**A verdict, from which the harness builds the corrected copy.** You do not retype the record: the
harness copies it to a separate file and applies exactly the changes your verdict lists, so every
field you do not change stays as the researcher wrote it. Write the verdict to the path the harness
gives you and write no other file.

The verdict carries:

1. **`changes`** — the new value of each field you change, and only those: `status`, `ai_role`,
   `resolution_direction`, `no_change_found`, `counterexample.is_counterexample`, `ai.basis_quote`,
   and — where the event the status rests on changes — `event` (the full new object),
   `credited_humans` and `status_sources`.
2. **`outcome_prefix`** — where `event` changes, one sentence describing the new event. The harness
   puts it in front of the original `outcome`, marked as judged.
3. **`corrections`** — one entry per changed field: `field`, `from`, `to`, `why`. Start `why` with
   the failure mode it corrects (`"F1: …"`, or `"other: …"`) and point it at the evidence — a
   sentence of the record, a source — not at your general sense of the problem. The harness adds
   the date and marks the entry as this pass's. **Where you examined a code and kept it** but had
   real doubt, add an entry with `from` equal to `to`, giving the doubt; not where you simply agree.
4. **`judgement`** — your answers, as below.

```jsonc
"judgement": {
  "events": [{
    "id": "broe-2026",
    "what": "Broe proves the Tate conjecture for abelian fourfolds over finite fields",
    "date": "2026-08-19", "precision": "day", "after_snapshot": true,
    "source": "https://arxiv.org/abs/2608.28651",
    "scope": "case",                  // whole | case | bound | instances | variant | none
    "verification": "unreviewed",     // digested | checkable | unreviewed
    "credibility": "credible",        // credible | doubtful | not_credible | knocked_down
    "credibility_reason": null,       // required unless credible
    "ai_role": "none",                // generated | assisted | none
    "ai_basis": null,                 // the quote you relied on, if not none
    "direction": "confirmed",         // refuted | confirmed | mixed | null
    "is_counterexample": false
  }],

  "rests_on": "broe-2026",            // the event id, or null when nothing survives

  "derived": {                        // from §4, mechanically; after your changes the codes must equal these
    "status": "partial",
    "ai_role": "none",
    "resolution_direction": "confirmed"
  },

  "changed": ["status"],              // fields you changed in the copy; empty when you agreed
  "doubts": "Anything a later reader should know that is not a change.",
  "insufficient_evidence": false,     // true when the record could not be judged (F16)
  "confidence": "high",               // high | medium | low
  "searches": ["verbatim query", "…"]
}
```

**Never add a fact that is not in front of you.** Every name, date, identifier and source in your
verdict must appear in the record or in a page you opened in this run. Where the record gives only
surnames, give only surnames; where it gives only a month, give only the month. A gap is honest; a
plausible first name is fabrication.

**Never delete evidence.** Where the AI role changes because the quote in `ai.basis_quote` belongs
to a different event, leave the quote in place and explain in the correction. Replace it only with
a quote that supports the new role.

### Before you return, check

1. The record's codes with your `changes` applied equal `derived`, and every change has a
   `corrections` entry.
2. The event `rests_on` names is the one the codes describe, including the AI role.
3. Nothing you discarded in step 1 is setting the status.
4. A `whole` scope survives a re-read of the bullet's exact wording.
5. `not_credible` has several F5 signals, not just an absence of review.
6. You wrote the verdict file and nothing else.
