# Audit — sonnet-2026-09-22

What was measured, how, what went wrong, and what is still missing. Written for whoever picks this
up next and has to decide how much of it to believe.

The findings themselves are not restated here: each of the 457 records under
`deepdive/mark_2026-09-22/out/` carries its own queries, sources, confidence and the strongest case
against its own classification. This document is about the *method*.

## 1. What was produced

457 problems — the 467 bullets of the 26 January 2024 revision, less ten the article uses as
headings. One agent per problem, its own context, following `DEEP_DIVE.md`.

| | |
|---|---|
| Problems researched | 457 |
| Moved since the snapshot | 194 (42%) |
| AI involved | 43 (9% of all, 22% of those that moved) |
| Status | open 241 · partial 95 · progress 70 · claimed 20 · open_stale 22 · resolved 9 |
| AI role | none 414 · generated 27 · assisted 16 · incident 0 (`bound` retired, see §4) |
| Named systems credited | 35 |
| Mean sources opened per record | 9.3 |

These are the figures **after** the hand corrections in §4, which are the current state of the data.
As the research left it they were: moved 229 (50%, counting the 22 `open_stale` rows the coding
rules say are not changes), AI involved 53, status open 228 · partial 81 · progress 67, AI role
none 404 · incident 6, named systems 42. "Moved since the snapshot" here means `resolved`,
`claimed`, `partial` or `progress` — `open_stale` is excluded, since those were settled before the
frozen revision and are not movement within the window.

**Nine more records were set aside as non-credible claims on 24 September 2026, and a further
twenty `claimed` records were recoded as partial results or progress** — see "Claims not credible
enough to count" and "Claimed rows that were never claimed resolutions" in §4. They are the reason
the table above differs from the counts quoted in the paragraph below and in §4's earlier
subsections, which were written before them. **Resolutions (`resolved` + `claimed`) now number 29,
not the 58 of the morning of 24 September.**

**Eleven records were changed by hand, and `incident` is now empty.** Every one carries a
`corrections` entry naming the change, the reasoning, and the fact that a human made it. Four
statuses moved to `open` because the only event on the record was a claim that had been withdrawn
(`collatz-conjecture`, `is-there-a-covering-system-with-odd-distinct-moduli`,
`do-siegel-zeros-exist`, `yang-mills-existence-and-mass-gap`); two moved to `open` because the
event predated the frozen revision (`novikov-conjecture`, `gaussian-moat-problem`);
`inscribed-square-problem` kept `progress` but had its event re-pointed from a withdrawn
self-published claim to the Greene–Lobb advance that was already described in the same record;
`hopf-conjecture` moved from `incident` to `none`; `inverse-galois-problem` from `assisted` to
`none`; `sphere-packing` from `claimed`/`generated` to `progress`/`bound`; and
`moving-sofa-problem` was reviewed and left as coded. **That the `incident` code now has no members is a consequence, not a goal** — see §4.

**Cost.** Triage: $0.199 per problem measured, ~$92 for the sweep. Deep dive: ~$0.49 per record,
derived from billing against records written (287 records against $140 on one day), so roughly
$225 for the full set. A single cold-start probe measured $1.14, more than double the batch rate —
85% of the spend is re-sending the system prompt, which a warm prompt cache makes nearly free, so
never price a batch from one call.

## 2. The two passes, and why only one of them counts

A cheap triage pass (`TRIAGE_INSTRUCTIONS.md`, one agent per problem, 3–5 searches) was built to
decide which problems deserved the expensive pass. It swept 462 bullets and returned 183 `likely`,
64 `possible`, 210 `none`.

Every `none` was then deep-dived anyway, which turns its accuracy from an assumption into a
measurement:

| verdict | problems | moved | hit rate |
|---|---|---|---|
| `likely` | 183 | 174 | 95% |
| `possible` | 64 | 31 | 48% |
| `none` | 210 | 24 | **11%** |

**As a filter it fails.** 24 problems it passed over had moved — including a claimed refutation of
the **Hopf conjecture** (Brendle and Hung, arXiv August 2026), a case of **Rokhlin's problem**, a
sub-case of the **elementary embedding** question, and the **Erdős–Faber–Lovász** conjecture, which
was settled for large *n* in 2021 and therefore `open_stale`. Those are not marginal misses.

**As a prioritiser it works.** `likely` is right 19 times in 20, and `possible` behaves as a hedge
should — about a third of it real. So the pipeline keeps triage as a head start for each deep-dive
agent and lets it gate nothing. `deep_dive.py` runs without it.

**The selection was also gating the validator, which nobody noticed until 24 September 2026.**
`check()` iterated the selected keys, so it validated 247 records while 457 sat on disk: the 210
researched outside the selection were never examined by any automated rule. `hopf-conjecture` is
the case in point — triaged `none`, deep-dived anyway, carrying a claimed refutation of the product
form, and never once validated. `check()` now iterates every record in `out/` and reports the
selection separately, so the run prints *"457 records validated of 462 problems (247 of the 247
selected, plus 210 outside the selection)"*. The fix was tested by planting a violation on an
unselected record and confirming it is caught. **A filter on which problems get researched is not a
filter on which results deserve checking**, and the two had been the same list.

(462 rather than 457 because `problem_keys.md` can only identify five of the ten headings on its
own; the other five are known from the triage records alone, which is the last item in §7. They
have no records, correctly, and are not reported as missing.)

**The audit sample overestimated the damage.** Before the full sweep, 25 randomly drawn `none`
problems were deep-dived as a miss-rate probe and 6 came back moved — 24%, against a true rate of
11%. A 12% sample of 210 gives a wide interval; the point estimate happened to land high. The
sample was still what prompted finishing the set, which was the right call for the wrong number.

## 3. What went wrong during the run

**175 records were written with no searches behind them.** Adding `--bare` to the agent invocation,
intending to force API-key billing, silently disabled the `WebSearch` tool. The agents fell back to
`curl`, which the sandbox blocks, and — correctly following the instruction that a failed search is
not an empty one — recorded `possible` with an explanation. The split by time is unambiguous: 0 of
254 records before the change, 175 of 208 after. The flag was removed, the affected records
quarantined under `triage/2024-01/quarantine-nosearch/`, and the problems re-run. **An agent
faithfully reporting a broken tool still produces unusable data at scale; the validator now rejects
any record with no queries.**

**Two rules were ambiguous enough that agents applied them inconsistently.**

- **§6.2 (`ai_role`).** The Carathéodory conjecture was coded `assisted` on a quote that
  disqualifies it — the authors say Claude "helped check the construction" and Codex "aided
  formalization", both explicitly excluded. The code name matched the word the source used, and the
  exclusion lived in prose below the table where the decision is made. Fixed by moving the
  exclusion into the `none` row and restating `assisted` as *producing mathematics that is in the
  result* rather than "a substantial part".
- **§6.4 (`resolution_direction`).** The document never said what the direction was a direction
  *of* — the event, or the problem's fate. 10 of 59 records left it null on a `partial`, reasoning
  that the problem itself was not settled. Fixed by naming the referent (the event the status rests
  on) and requiring it for `resolved`, `claimed` and `partial`.

**A third gap survived into the final data** and was corrected by hand: nothing said an exhibited
counterexample cannot be recorded as `confirmed`. §6.4 now says so, and adds that an object
answering an existence question affirmatively is a witness, not a counterexample.

## 4. Corrections made after the research

Five records were changed by a consistency pass rather than by the researching agent. Each carries
a `corrections` entry with the field, the old and new values, and why. They are listed in
`deepdive/mark_2026-09-22/REVIEW.md`.

| record | change |
|---|---|
| Borsuk's problem | `resolution_direction` confirmed → refuted (the object contradicts the conjecture) |
| beggar-my-neighbour | `is_counterexample` true → false (a witness, not a counterexample) |
| Harborth's conjecture | `predates_frozen_revision` false → null (a year-only 2024 date cannot place it either side of 26 January) |
| spherical Bernstein's problem | event repointed from a 2026 preprint to the pre-snapshot resolution the record's own summary describes, which is what `open_stale` rests on |
| Guralnick–Thompson | `no_change_found` true → false (a pre-snapshot resolution was found) |

A scan for the same classes of contradiction across all 457 found nothing else: no date/flag
mismatches, no `open_stale` with a post-snapshot event, no AI role without a supporting quote, no
`no_change_found` paired with a non-`open` status.

**Two further records carry a `corrections` entry that changes nothing.** Both were examined by
hand on 24 September 2026 and left as the agent coded them; the entry records the reasoning so the
call is visible to anyone recounting these numbers, with `from` and `to` identical to mark it a
retention rather than a change.

| record | call |
|---|---|
| Hopf conjecture | `status` retained `claimed` (the preprint is not withdrawn and the authors have not conceded, so an AI-disputed claim is still a claim). `ai_role` was first retained as `incident` and then, on review, **changed to `none`** — see below |
| moving sofa problem | `ai_role` retained `bound` |

Both were found by the same scan, which is worth keeping: **for each AI-credited record, does the
AI's own sources intersect the sources of the event the status rests on?** Across all 53, exactly
these two come back disjoint.

- **The moving sofa** is the clean case of one `ai_role` per problem flattening two events. The
  credit is Leng et al.'s July 2024 neural-network bound (2.37 → 2.3337, arXiv:2407.11106); the
  status is Baek's November 2024 preprint (arXiv:2411.19826), which this record describes as a
  purely human, non-computer-assisted proof. So a query for *resolutions involving AI* returns this
  row although the claimed resolution contains no AI at all. It is also the only resolved-or-claimed
  row whose AI credit has no canonical system behind it, `model_aliases.py` having deliberately
  mapped "piecewise linear neural networks" and "physics-informed machine learning" to nothing.
- **The Hopf conjecture** was the harder case, and it was **recoded `incident` → `none`**. The
  claim is human (Brendle–Hung, with Mathematica, which is computer algebra and not an AI system);
  the AI (Refine) arrived from outside, a day later, as a critic, reporting a bug under a key
  second-order-positivity calculation and an unclosed gap in a uniform bound. `incident` is defined
  as *an AI-produced claim later withdrawn*, and neither half holds — the claim is not AI-produced
  and it has not been withdrawn. An AI arguing that a human claim is *wrong* is not AI involvement
  in producing it, and §6.2 files checking under `none`. The Refine episode stays in `summary`,
  `disputes` and `ai.basis_quote`; only its weight in the counts changes. **§6.1 and §6.2 offer no
  code for an AI that refereed someone else's mathematics, so this row sits in `none` for want of
  anywhere better — a gap in the scheme, not a finding that Refine did nothing.**

**Two rules govern a problem carrying more than one event**, and the sofa is the worked example of
the first:

1. **Different tiers: the furthest event wins.** `status` and `ai_role` both describe one event,
   the furthest the problem has got — resolved/claimed over partial/progress over open. The sofa's
   AI bound is progress; Baek's claimed proof is a resolution, so the row reads human. The reason
   is supersession rather than seniority: once an exact optimum near 2.2195 is proved, an upper
   bound of 2.3337 is not a lesser result but a dead one.
2. **Same tier: AI counts if AI did any of it.** Two bounds moved on a still-open problem, one by a
   model and one by humans — neither supersedes the other and the model did move the problem, so
   the credit holds. Rule 1 is about supersession, rule 2 about addition.

**The sofa is now fixed in the data** (`ai_role` `none`, since `bound` was retired — see "`bound`
retired" below). The paragraph that follows is kept as written before that: `bound` counted
toward incomplete movement and never inside the resolution numerator. On that rule the AI share of
the 59 resolutions is 25 (42%), not 26. **Live contingency:** Baek's proof is `claimed`, under
review at Annals since late 2024. If it fails, the furthest event reverts to the AI bound and the
row becomes an AI one at tier progress.

**What the Hopf recode did to §6's split.** That row rests on an exhibited counterexample, so
recoding moved a counterexample from the AI column into the human one: **11 of 26 AI-involved
(42%) against 8 of 33 without (24%)**, where it had been 12 of 27 (44%) against 7 of 32 (22%). The
direction is unchanged; the gap narrows from 2.0× to 1.75×. Excluding the sofa from the resolution
numerator as well gives 11 of 25 (44%) against 8 of 34 (24%). `incident` now stands at 5 records,
and Refine is no longer a credited system, taking the model table from 42 to 41.

### Withdrawn claims, and why `incident` is now empty

Five records rested on an AI claim that had been announced and then withdrawn. §6.1 directs exactly
that — "a withdrawn claim is still an event", recorded as `progress` with `ai_role: incident` — and
every agent followed it correctly. **These corrections override that instruction.** The instructions
are deliberately left unedited, so those records and the document they were produced under now
disagree on this point; each record says so in its own `corrections` entry.

The rule applied instead: *a withdrawn claim leaves the problem exactly where it was, so it is not
the event the status rests on. Discard it, take the furthest genuine event that remains, and let
`status` and `ai_role` both follow that.*

| record | what was discarded | what remained | now |
|---|---|---|---|
| `inscribed-square-problem` | Ueoka's self-published claim, acknowledged broken | **Greene–Lobb, arXiv:2407.07798** — a Lipschitz threshold moved on a restricted case, no AI claimed | `progress` / `none`, event re-pointed |
| `collatz-conjecture` | Kumar's Lean "disproof" | nothing qualifying: verification to 2⁷¹ is one more example of a universal claim, and the density-bound improvement rests only on the claimant's own repository | `open` / `none` |
| `is-there-a-covering-system-with-odd-distinct-moduli` | the Aristotle claim, conceded false in four days | nothing: Mian–Siddique formalise an *already-known* folklore bound, which moves no mathematics and is `none` under §6.2 | `open` / `none` |
| `do-siegel-zeros-exist` | Louiz's ResearchGate preprint, resting on a misreading of Heath-Brown | nothing | `open` / `none` |
| `yang-mills-existence-and-mass-gap` | a Zenodo report among dozens of comparable crank preprints | nothing | `open` / `none` |

Only the first had genuine mathematics underneath, and the agent had written it into the same
record before choosing the more eventful item as the dated event. The other four had nothing.

**Three of these were noise rather than failure, and that distinction matters.** Collatz and the
covering-systems claim were serious artifacts: a sorry-free Lean proof that passed two independent
checkers and exposed two real kernel soundness bugs, and a formalised proof attempt on an Erdős
problem from Harmonic's Aristotle. Siegel zeros, Yang–Mills and the inscribed square were
self-published work by non-specialists that happened to use a model to write Lean. Counting the
latter as AI involvement would have made the AI totals partly a measure of where cranks point their
tools — those three rows alone credited Grok, Gemini and Claude on this list.

**Consequence: no record now carries `ai_role: incident`.** The code is still defined in §6.2 and
still describes something real; it simply has no members once withdrawn claims stop setting the
status. Anything that reports per-code counts should say the category is empty rather than omit it,
and a future run following §6.1 as written will repopulate it.

**One asymmetry worth noticing in the two Lean cases.** On `hopf-conjecture` an AI verifier (Refine)
caught a bug in human work. On `is-there-a-covering-system-with-odd-distinct-moduli` an AI verifier
(Aristotle) reportedly passed a formalisation 7 checks out of 7 while it contained a provably false
axiom, which a human then found. Both are in the prose of their records and neither is counted.

### Two rows where the code did not match what the record said

Both were corrected by hand, and **neither departs from the instructions** — each applies a rule as
written, where the original coding did not. That distinguishes them from the withdrawn-claim group
above, which overrides §6.1.

**`inverse-galois-problem`, `ai_role` `assisted` → `none`.** The authors' disclosure is almost
entirely activity §6.2 excludes by name — "searching the literature, code generation, testing
hypotheses, ruling out other approaches, devising computational strategies, checking our results,
and proofreading our manuscript" — bracketed by "No text in this article was written by AI" and
"Our final results were verified in Magma and PARI/GP without the use of AI." §6.2 asks what the
model produced that appears in the result; the mathematics in the result is the degree-23
polynomial with Galois group M23, reached by PSLQ and Belyi map construction in Magma and PARI/GP,
and nothing in the quote says a model produced any of it. This is the Carathéodory pattern §3
describes as fixed — the fix caught Carathéodory and missed this one. `status` stays `partial`.

**`sphere-packing`, `claimed`/`generated` → `progress`/`bound`.** The record's own first sentence is
"The general-dimension asymptotic sphere packing problem remains open", and its `competing_reading`
argues for `progress`, yet the row was coded as a claimed resolution. Three unrelated things
happened in the window and none settles the bullet: Klartag (April 2025) proved a new lattice
*lower* bound of order n²·2⁻ⁿ, pure human work; a Huawei Noah's Ark / UCL team (December 2025) used
Bayesian optimisation plus MCTS to improve upper bounds in dimensions 4–16; and OpenAI's Astra
(August 2026) determined the exact asymptotic exponent of the **Cohn–Elkies linear-programming
bound**. The status rested on the third, which is a theorem about how far a proof *method* can ever
reach — striking, and the first improvement to the general high-dimensional upper-bound exponent
since 1978, but a bound rather than a resolution. §6.2 is explicit that `bound` "is not a weak
`generated`": the problem is still open and what moved is a number. Astra keeps its credit; the row
moves out of the resolution counts and into incomplete movement.

Together these take resolutions from 59 to 58 and AI-involved resolutions from 26 to 25 (43%).

### Claims not credible enough to count, corrected by hand, 24 September 2026

Nine `claimed` records rested on a preprint that, on the record's own findings, is very unlikely
to be a proof, even though nothing has knocked it down yet. The correction was directed by a human
reviewer (Alex Fogelson) and drafted on that instruction by Claude (claude-opus-5-5); each entry's
`by` field says so. **No new sources were opened:** the calls rest on what each agent already found
plus general knowledge of the field, so they are judgements, not new research.

**These override DEEP_DIVE.md §6.1**, which codes any undigested preprint `claimed`. Every agent
followed that correctly. The rule applied instead extends the withdrawn-claim rule above: *a claim
with no expert uptake, from outside or at the margin of the field, on a problem whose resolution
would be a landmark, is set aside like a withdrawn claim; the furthest genuine event that remains
sets the status.* Each claim stays in `outcome`, `event` or `summary` as evidence, and any of them
should revert if it is ever digested.

| record | set aside | why | now |
|---|---|---|---|
| `montgomerys-pair-correlation-conjecture` | Jerby, arXiv:2511.18275 | Full-range GUE pair correlation under RH is far beyond known methods; no uptake in ten months; the live article covers adjacent 2025 work but not this | `open` |
| `values-of-g-k-and-g-k-in-warings-problem` | Root, arXiv:2508.17950 | Needs the fractional parts of (3/2)ᵏ controlled for every k — Mahler-3/2 territory, where only an ineffective large-k result exists; author outside the field; only an automated review | `open` |
| `yaus-conjecture-on-the-first-eigenvalue` | Zeng, arXiv:2508.06123 | Two later 2026 papers bounding the same eigenvalue still call it open and do not mention it | `progress`, event re-pointed to arXiv:2606.10962 |
| `cherns-conjecture-affine-geometry` | Cocos, arXiv:1504.04852 v4–v12 | "Flat affine" is the whole conjecture, not a sub-case; nine major revisions in 2025; author's own talk calls it "a posible proof"; two predecessor proofs withdrawn | `open` |
| `albertson-conjecture` | Sadhu, arXiv:2609.01682 v2 | Scope jumped from r≤26 to every r in twelve days; solo; automated review only | `partial`, event re-pointed to Cranston's r≤24 |
| `hermites-problem` | Tagnon, arXiv:2608.23281 | Evidence is sampled certificates for a universal statement, and the abstract says the general problem remains open — the Collatz rule | `open` |
| `littlewood-conjecture` | Lazar, arXiv:2202.01596 v2 | Pre-window preprint re-dated by a "minor changes" revision; no citation in four years; the restricted class is unspecified | `open` |
| `abc-conjecture` | Joshi, arXiv:2403.10430 and sequels | Restates the IUT dispute; Scholze unconvinced, no journal, and the LANA formalisation declines to call IUT a proof | `progress`, event re-pointed to Bernert–Browning–Lichtman–Teräväinen's O(N^(33/50)) exceptional-set bound |
| `whitehead-conjecture` | Kawauchi, arXiv:2303.04368 v2 | Pre-window v1; published only in a venue with predatory red flags; no topologist engagement | `open` |

The abc re-point overrules the agent on one point: it declined to count the exceptional-set bound
under the existence/infinitude rule, but that rule is about one more example of an existence
claim, and this moves a bound on the conjecture's own quantity, the number of exceptions.

`does-there-exist-an-o-minimal-first-order-theory-with` (Chernikov's "(maybe)" manuscript) was
considered and **left `claimed`**: it comes from an established model theorist and carries a
zero-`sorry` Lean development on Mathlib, which is real evidence unless the Lean statement
mistranslates the problem.

**All nine were human, non-AI confirmations, and that moves §6.** Resolutions fall from 58 to 49
and AI-involved resolutions stay at 25, now 51%. The counterexample split becomes **11 of 25
AI-involved (44%) against 8 of 24 without (33%)**, where it was 24%. The direction survives; the
gap narrows from 1.8× to 1.3×. That is the risk with this kind of correction: undigested human
claims were inflating the non-AI denominator, and removing only the implausible ones is itself a
judgement that falls on one side of the split.

### `bound` retired as an AI role, 24 September 2026

At the reviewer's direction `bound` is no longer an `ai_role`. It named the kind of result — a
bound moved on a still-open problem — which `status: progress` already records, so it put a status
distinction onto the attribution axis. That is the conflation the site's `attrOf` fold existed to
undo, and the fold is gone with it. The nine records were recoded by the §6.2 test of what the
model produced, each with a `corrections` entry:

| record | now | basis |
|---|---|---|
| `riemann-hypothesis` | `generated` | "A proof … was produced by an internal research version of Claude … and subsequently verified" |
| `twin-prime-conjecture` | `generated` | the H1 = 186 proof "is due to GPT 6 Astra" |
| `sphere-packing` | `generated` | Astra "produces the core insight and strategy for a proof" |
| `hadamards-maximal-determinant-problem` | `generated` | the RL system found the record matrices; checking a determinant is computation. Thin quote, flagged |
| `hadwiger-conjecture-graph-theory` | `assisted` | "central proof idea … developed with the assistance of" two models, refined by the author |
| `erdos-gyarfas-conjecture` | `assisted` | ChatGPT "materially assisted … preliminary arguments" |
| `conways-99-graph-problem` | `assisted` | AlphaEvolve produced one search heuristic in a human-led paper |
| `resolution-of-singularities` | `assisted` | AlphaEvolve evolved the candidate ranking functions; whether the toy-model paper counts as `progress` at all is flagged for a second look |
| `moving-sofa-problem` | `none` | rule 1: the furthest event is Baek's human claimed proof |

`generated` on a `progress` row means a model produced the bound, not that it solved the problem;
the status still says which. Counts: AI role none 412 · generated 27 · assisted 18. On the 49
resolutions nothing changes except the sofa, which the counting rule already excluded: **24
AI-involved (49%)**, and the counterexample split reads **11 of 24 AI-involved (46%) against 8 of 25
without (32%)** — the "excluding the sofa" variant above, now the only one.

DEEP_DIVE.md §6.2 still defines `bound` and is left unedited. `deep_dive.py` no longer accepts it,
so a future run that emits it fails validation rather than reaching the site, where it no longer
has a label.

### Claimed rows that were never claimed resolutions, corrected by hand, 24 September 2026

Directed by the reviewer (Alex Fogelson), drafted by Claude (claude-opus-5-5) from each record's
own findings; no new sources were opened. Every remaining `claimed` row was reviewed against two
questions: **does it claim the whole problem the bullet states, and is the claim credible?**

**The cause is in the rules, and it is the same conflation as `bound`.** `status` carries two
independent things: how much of the problem was settled (all of it, a case, a bound) and whether
an expert has checked it. §6.1 defines `claimed` for an undigested *resolution*, but agents read it
as "undigested, whatever it is" — several records say so outright ("per §6.1's rule that a case
settlement without expert digestion is `claimed`"). An unreviewed special case therefore landed in
the same category as an unreviewed full proof, was counted as a resolution, and was shown on the
site as "Proved (claimed)". Birch and Swinnerton-Dyer and the Tate conjecture were among them.
None of these records is wrong about the mathematics; each says in its own summary or
competing_reading that the result is a case. The instructions are left unedited; splitting status
into scope and verification is the durable fix and is not done here.

**Recoded as `partial`** — a case, or one named part of a multi-part bullet, settled (direction kept):

| record | what was settled |
|---|---|
| `birch-and-swinnerton-dyer-conjecture` | BSD for infinite, density-zero families of quadratic twists |
| `tate-conjecture` | abelian fourfolds (and fivefolds) over finite fields |
| `cartan-hadamard-conjecture` | dimensions 3–9 |
| `big-line-big-clique-conjecture` | the case k = 6, ℓ = 4 |
| `values-of-the-hermite-constants-for-dimensions-other-than` | γ₉ = 2, one of the values asked for |
| `rysers-conjecture` | the case (r, ν) = (4, 2) |
| `tuzas-conjecture` | graphs of maximum degree 7 |
| `arnold-givental-conjecture` | the Arnold–Givental half of a bullet that also names the Arnold conjecture |
| `arthurs-conjectures` | unitarity of Arthur packets for real groups, one component |
| `is-the-borel-monadic-theory-of-the-real-order` | the first of two questions |
| `hopf-conjecture` | the product form refuted; the sign form untouched |
| `fugledes-conjecture` | dimension two only; R still open |
| `rendezvous-problem` | the Anderson–Weber conjecture, one sub-problem |
| `fontaine-mazur-conjecture` | GL(2) cases; event re-pointed from Zhang's doubtful p = 3 claim to Thorne (arXiv:2608.07186) |

**Recoded as `progress`** — a bound or record moved (direction set to null):
`borsuks-problem` (smallest counterexample dimension 64 → 63; the conjecture itself fell in 1993),
`degree-diameter-problem` (two records), `find-the-value-of-the-de-bruijn-newman-constant` (upper
bound on Λ), `universal-point-set` (n^(1+o(1)) upper bound; the linear-versus-almost-linear gap
remains), and `1-3-2-3-conjecture`, where the claimed event — a census of posets on at most 14
elements — is finitely many instances of a universal claim (the Collatz rule), so the event
re-points to Aires–Kahn's asymptotic bounds and `ai_role` goes `assisted` → `none`.

**Set aside as knocked down** — `are-gamma-the-euler-mascheroni-constant-pi-e-pi` → `open`, `ai_role`
→ `none`: Wachs found the key inequality in Sun's Catalan's-constant proof fails numerically, a
partial Lean formalisation agrees, and nothing else in the window touches any named constant.

**Reviewed and retained, with doubt** — `casas-alvero-conjecture`, `buchis-problem`,
`mean-value-problem`, `ibragimov-iosifescu-conjecture-for-mixing-sequences` and
`does-there-exist-an-o-minimal-first-order-theory-with` each claim the whole problem and each carry a
`from` = `to` entry giving the doubt. For the two unsteered GPT-6 Astra disproofs the doubt is
specific: whether the Lean *statement* matches the conjecture (the kernel cannot catch a
mistranslated hypothesis, and φ-mixing has no Mathlib definition to lean on). Navier–Stokes was
left for separate review. `crouzeixs-conjecture` may deserve an *upgrade* — Crouzeix himself,
Greenbaum and Townsend read the proof — which is outside this pass.

**Twenty claimed rows remain**, all claiming the whole problem. **Resolutions fall from 49 to 29;
AI-involved from 24 to 16, now 55%.** Of the twenty recoded, eight had an AI role, and the
counterexample split in §6 moves to **10 of 16 AI-involved (63%) against 5 of 13 without (38%)**:
Hopf, Fuglede and the rendezvous problem were human refutations and are now partial, Borsuk an AI
one and now progress.

**The site now separates the three meanings of a direction.** Cards and the table show "Proved" /
"Refuted" only on `resolved` and `claimed` rows, "Case proved" / "Case refuted" on `partial` rows,
and nothing on `progress`. The same fix removed a card bug: the status badge and status box were
appending `outcome` — the full prose sentence, unescaped — as though it were a short label.

### Unversioned system names

`ChatGPT`, `Claude`, `Codex`, `Claude Code`, `Gemini`, `Grok` and `GitHub Copilot` name a product
or family, not a model. `build.py` now shows each as "`<name>` (unknown version)" in every output —
site, JSON, CSV and SQLite — via `UNVERSIONED` in `model_aliases.py`. Canonical keys are unchanged
because `release_dates.json` is keyed on them. A source string that carries its own version is
kept verbatim: "OpenAI Codex (GPT-5.6 family)" is not rewritten.

These names also **carry no release date**. The release pass had dated each to its product line's
launch (Claude to March 2023, ChatGPT to November 2022, Codex to 2021, Claude Code to 2025), which
put them on the release-date chart as though they were specific models. `build.py` now blanks the
dates for every `UNVERSIONED` name and marks them `release_confidence: unversioned`, so they are
off the release timeline and never set `predates_availability`. The researched dates stay in
`release_dates/` untouched.

## 5. Judgement that is not the agents'

Two files hold every human decision made after the research, and both are worth reviewing before
the numbers are published.

**`pipeline/model_aliases.py`** maps 88 raw system strings to 42 canonical models. The records name
systems exactly as their sources do, which is right for evidence and useless for counting: "GPT 5.6
Sol", "gpt-5.6-sol" and "Chatgpt 5.6 Solar" are one model.

Labs were mostly read off the records' own summaries, which name the owner in passing — "Harmonic's
Aristotle theorem-proving system", "Axiom Math's AxiomProver", "a Peking-University-led team
introduced PackingStar", "Yuksekgonul et al.'s TTT-Discover", "Ye et al.'s SimpleTES". Two needed
the web: Refine, the verification tool that found gaps in the Hopf conjecture preprint, is Refine
Technologies; the Danus system is a multi-agent proof orchestrator from a Peking-University-led
group (arXiv:2607.06447). Only `unnamed model` now has no lab, which is what it is for.

Entries marked `REVIEW` are guesses from the string alone — whether an unqualified "ChatGPT 5.6"
means the base model or a tier. Three strings map to nothing deliberately: PPO, "piecewise linear
neural networks" and "physics-informed machine learning" are an algorithm and two method
descriptions, not systems.

**A system named on a record is not a system credited.** 21 records name one or more systems while
coded `ai_role: none` — a model that checked a construction, wrote prose, or was tried and failed.
The clearest case is the Petersen-minor bullet, where the authors disclose that "GitHub Copilot was
used to assist in implementing parts of the authors' verification software" and that ChatGPT Pro
and Gemini Deep Think helped with exposition. Those names stay in the record as evidence but
contribute nothing to `ai_models`, so they cannot show up as models credited on a problem. Fixing
this took the model table from 45 to 42 — Gemini Deep Think, GitHub Copilot and Xiaozhua appear
only on uncredited records — and cut the leading counts appreciably: GPT-5.6 Sol 16 to 13, GPT-6
Astra 13 to 12, Codex 5 to 3, Claude 7 to 3.

**`pipeline/join_map.py`** carries five entries, for the Millennium problems the page names in its
introduction rather than in a field list. The other 452 join on statement text, which matches
exactly because both sides run the same `strip_wiki`.

**The ten headings** were identified from two disjoint sources of five: `problem_keys.md` flags a
bullet whose text ends in a colon and has children (Sudoku, Chess, Go, Tic-tac-toe variants,
Tutte's conjectures), and the triage pass marked five more `skip` by judgement (Kaplansky's
conjectures, the Deligne conjecture, Landau's problems, and two "Problems in …" headings). Neither
heuristic alone is complete. They stay in the dataset flagged `is_grouping`, excluded from every
count.

## 6. A result worth noticing

Of the 29 problems now `resolved` or `claimed`, 15 rest on an exhibited counterexample. Split by
who did the work: **10 of 16 AI-involved (63%) against 5 of 13 without AI (38%)**. Narrowing to the
13 resolutions a model produced outright gives **9 of 13 (69%)**. An object that breaks a
conjecture is a different kind of result from a universal proof — one person can check it — which
is why the two are counted apart. With numbers this size the difference is suggestive, not
conclusive, and the sharpest version of it rests on the smallest base.

(As the research left it this read 12 of 27 against 7 of 32, a 2.0× gap. Two §4 corrections moved
it: Hopf is itself a counterexample row, so recoding it carried one case across the divide and
narrowed both sides at once, and the sphere-packing recode removed a non-counterexample from the AI
side. It then read 11 of 25 against 8 of 33 (24%) until the nine non-credible human claims in §4
were set aside, taking the non-AI side to 8 of 24, and the sofa's recode from `bound` to `none`
moved one non-counterexample row across, giving 11 of 24 against 8 of 25. Recoding twenty claimed
rows as partial results or progress (§4) then took out three human refutations and one AI one,
giving 10 of 16 against 5 of 13. The finding survives every variant tried; its size does not, and
on 29 resolutions the base is now smaller than ever.)

Also worth a human read before publication: the nine `resolved` records, particularly the cycle
double cover conjecture (credited to GPT-5.6 Sol Ultra), Sendov's conjecture and the Jacobian
conjecture. `resolved` requires expert digestion, and those are the highest-stakes claims here.

## 7. Known gaps

- ~~**`year_introduced` is not researched.**~~ **Closed 23 September 2026.** When this section was
  written only the five Millennium problems carried a year. Years were researched afterwards and
  **401 of 457 now carry one** — 241 from the mathematical literature (sourced), 150 from the
  Wikipedia article lead, 9 from an infobox, 1 recalled — leaving 56 undated and 13 flagged
  approximate. The Problem Ages tab draws over those 401 rather than saying it cannot.
- ~~**Model release dates are not researched.**~~ **Closed 23 September 2026.** All 42 were null
  when this was written. They were researched afterwards, one system per agent run, by
  `pipeline/release_dates.py`: **35 sourced, 1 carried from a base model's dates (`tier`), 5
  `none_exists`, 1 `unresearched`.** The distinction this gap asked for — "researched, none exists"
  against "not researched" — is what `release_confidence` records, so the Resolutions by Model
  Release Date chart has data behind it.
- **Most 2026 items are unrefereed.** `resolved` means digested by experts, not peer-reviewed.
- **`page.wiki` and `page_history.json` were copied** from `opus-5-2026-09-18` rather than
  re-fetched. Both fetch scripts regenerate them; the version is not self-derived until they run.
- **Five of the ten headings are only identifiable from the triage records.** A from-scratch run
  that skips triage will research those five as if they were problems.
