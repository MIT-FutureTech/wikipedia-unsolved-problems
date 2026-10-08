# Design notes — what v1's coding scheme got wrong

Written October 2026 while designing version 2 of the dataset, against the v1 rules in
`prompts/DEEP_DIVE.md` as they stood when `data/mark_2026-09-22` was produced. They record where
v1's scheme proved ambiguous, what the audit had to correct by hand afterwards, and what was under
discussion for v2.

They lived inside `DEEP_DIVE.md` itself, marked so that research agents would skip them, because
that document had to stay frozen while `data/mark_2026-09-22` was being produced from it. They are
here instead now that the document has been rewritten: it no longer asks the research pass to
classify anything, so most of what these notes criticise is gone from it.

**What the rewrite took from them.** The research pass now collects evidence and the judging pass
(`prompts/JUDGE.md`) assigns every code, so the three fused questions inside `status` and the three
inside `ai_role` are separated by construction rather than by a better table. The record carries an
`events` array, as the sofa note proposes. Systems that were used but did not contribute to the
mathematics are recorded per event instead of vanishing into `none`. Withdrawal is an observation
attached to an event, not a role. `formalisation_only` is gone, replaced by naming what each system
actually did.

**What is still open.** Whether the derived status should publish both cuts (with and without the
set-aside claims); whether `confidence` earns its place; and the exact derivation rules when two
events on one problem are at the same tier. The headline figure of the nine set-aside rows — all
nine human, non-AI, moving the AI/non-AI counterexample split from 1.8x to 1.3x — is the reason the
derivation needs to be a dial set once rather than a judgement made 457 times.

Each note below is reproduced exactly as written, under the v1 section it annotated.

---


## On v1 §3.1 Which results count: scope, not size

> **⚠ v2 NOTE — this rule was misapplied in both directions.** It is correct as stated and still
> hard to apply, because it turns on a distinction the wording leaves implicit: *one more instance
> of a universal claim* moves nothing, but *a bound on the problem's own quantity* does.
>
> - On `abc-conjecture` an agent used this rule to decline Bernert–Browning–Lichtman–Teräväinen's
>   exceptional-set bound. That was wrong — the number of exceptions is the conjecture's own
>   quantity, so the bound moves it. The audit re-pointed the event by hand.
> - On `1-3-2-3-conjecture` an agent counted a census of posets on at most 14 elements as the
>   event. That was wrong the other way — finitely many instances of a universal claim. Re-pointed
>   to Aires–Kahn's asymptotic bounds, and `ai_role` went `assisted` → `none` with it.
> - `collatz-conjecture` is the clean case the rule gets right: verification to 2⁷¹ is one more
>   instance and counts for nothing.
>
> For v2 this is cleaner as a question about **scope** than as a question about what "counts":
> *did a quantity named in the bullet move, or did the set of checked instances merely grow?*


## On v1 §6.1 `status`

> **⚠ v2 NOTE — this single field is carrying three independent questions, and that is the largest
> known defect in the scheme.** The audit says so in its own words: *"splitting status into scope
> and verification is the durable fix and is not done here."* The three questions are:
>
> 1. **Scope** — how much was settled? (all of it / a case / a bound)
> 2. **Verification** — has a human expert checked it? (`resolved` vs `claimed`)
> 3. **Credibility** — should the claim be believed at all? (not represented anywhere)
>
> Each fusion cost real corrections:
>
> - **Scope × verification.** Agents read `claimed` as "undigested, *whatever it is*" and several
>   said so outright in their records — "per §6.1's rule that a case settlement without expert
>   digestion is `claimed`". So an unreviewed *special case* landed in the same code as an
>   unreviewed *full proof*, was counted as a resolution, and was shown on the site as "Proved
>   (claimed)". **Twenty rows were recoded by hand**, among them Birch and Swinnerton-Dyer (infinite
>   families of quadratic twists) and the Tate conjecture (abelian fourfolds over finite fields).
>   None of those records was wrong about the mathematics; each said in its own summary that the
>   result was a case.
> - **Credibility is absent entirely.** `claimed` covers both Chernikov's o-minimality manuscript —
>   an established model theorist with a zero-`sorry` Lean development on Mathlib — and a Zenodo
>   Yang–Mills report indistinguishable from dozens of crank preprints. **Nine rows were set aside
>   by hand** on a rule invented after the fact. The audit flags the danger in doing it that way:
>   all nine were human, non-AI claims, so removing them moved the headline AI/non-AI counterexample
>   split from 1.8× to 1.3×. *"Removing only the implausible ones is itself a judgement that falls
>   on one side of the split."*
>
> The v2 fix under discussion: make scope, verification and credibility three recorded fields, and
> **derive** this six-value status from them in the pipeline. The derivation reproduces these exact
> six labels, so nothing downstream changes — but the cut becomes a dial set once rather than 457
> individual judgements, and both numbers can be published.
>
> `JUDGE.md` §3 already does this, with Q2 scope (`whole`/`case`/`bound`/`variant`/`instances`/`none`),
> Q3 verification (`digested`/`checkable`/`unreviewed`) and Q4 credibility
> (`credible`/`doubtful`/`not_credible`/`knocked_down`), plus a derivation table in its §4. **The
> judge pass and this document are not in agreement**; the judge's version is the better one.


## On v1 §6.1 `status`

> **⚠ v2 NOTE — the bar is stated but nothing on the record proves it was met.** `status_sources`
> is a flat array of URLs. No field says *which* source is the digestion, *who* the expert was, or
> which of the three routes was taken, so a `resolved` call cannot be audited without reading the
> record's prose. The nine `resolved` rows cite 3–6 sources each with nothing marking the decisive
> one, and the validator in `deep_dive.py` only checks that the string is in the enum.
>
> **It erred in both directions.** `JUDGE.md` F12 found researchers were *conservative*: Crouzeix's
> conjecture was read and endorsed by Crouzeix himself plus two numerical analysts and still was not
> coded `resolved`. The twenty claimed→partial recodes went the other way.
>
> **`JUDGE.md` Q3 says several things this section does not**, and they are the operative ones: the
> expert must be **named**; automated review sites and AI referees are explicitly not experts (Pith
> Review, Refine, a lab's own "adversarial review panel"); a clean Lean build is not digestion; but
> informal expert reading *does* count when named and public — a blog post, a SIAM News essay, a
> doctoral committee approving the thesis containing the result.
>
> **Also worth saying plainly: `resolved` is a weaker claim than the word suggests.** It means
> digested, not refereed, and the audit's §7 notes most 2026 items are unrefereed. The cycle double
> cover row is `resolved` on an OpenAI announcement plus accompanying material — no journal, no
> referee.
>
> For v2 the proposal is a short ladder of **observable community events** — `asserted` / `posted` /
> `engaged` / `accepted`, with flags for which of four routes to `accepted` held — gathered by a
> dedicated pass with a fixed checklist of places to look, and the rung **derived** rather than
> chosen. The agent is then never asked whether a proof is correct, only what the community
> visibly did, which is a question research can settle.


## On v1 §6.1 `status`

> **⚠ v2 NOTE — the audit overrode this paragraph, and every agent had followed it correctly.**
> Five records rested on an AI claim announced and then withdrawn. Coding them `progress` made
> problems that had *not* moved look as though they had — the paragraph's own last clause concedes
> the problem did not move, then records movement anyway.
>
> The rule applied instead: *a withdrawn claim leaves the problem exactly where it was, so it is not
> the event the status rests on. Discard it, take the furthest genuine event that remains, and let
> `status` and `ai_role` both follow that.* Four of the five then had nothing left and became
> `open`; `inscribed-square-problem` had real mathematics underneath (Greene–Lobb) and became
> `progress` / `none` with the event re-pointed.
>
> **Consequence: no record now carries `ai_role: incident`.** The code is still defined in §6.2 and
> still describes something real; it simply has no members. A future run following this paragraph as
> written will repopulate it, and the records and this document now disagree on the point.
>
> **Three of the five were noise, not failure, and the distinction matters for v2.** Collatz (a
> sorry-free Lean "disproof" that passed two checkers and exposed two genuine kernel soundness bugs)
> and the covering-systems claim (Harmonic's Aristotle on an Erdős problem) were serious artifacts.
> Siegel zeros, Yang–Mills and the inscribed square were self-published work by non-specialists who
> happened to use a model to write Lean — and those three rows alone credited Grok, Gemini and
> Claude. Counting them would have made the AI totals partly a measure of where cranks point their
> tools.
>
> For v2: withdrawal belongs on a **standing** field attached to the event, not on the role or the
> status, and a discarded event should stay in the record as evidence rather than setting anything.


## On v1 §6.2 `ai_role`

> **⚠ v2 NOTE — what is strong here, and what is not.**
>
> **Keep:** the core test below (*what did the model produce that appears in the final result?*), the
> rule that the word a source uses is not the code, the requirement of the authors' own account with
> a quotable sentence, and `generated` surviving a human first author. Those four are the best
> design in the document and they handle the clean cases without strain — the OpenAI October 2026
> corpus is `generated` thirty times over and codes cleanly, with "the writeup was human edited for
> readability" being exactly the authors' account this section asks for.
>
> **Row by row, what is broken:**
>
> - **`none` is two opposite findings sharing one code.** The cell says it outright: *no AI system*
>   — **or** *a model was used and its contributions did not count*. **34 records name a system while
>   coded `none`.** So the dataset cannot answer *how often was a model in the room but not in the
>   result* — arguably the most valuable question it could answer, since it is the one nobody else
>   can: labs publish successes, and this is the only fixed-denominator measure of models being
>   tried and not contributing. It is also the quantity that should move fastest over time, so the
>   fusion costs the trend as well as the level.
> - **"suggesting strategies" does not belong in that exclusion list.** The other four items are
>   either not mathematics (proofreading, debugging) or mathematics that already existed (checking,
>   formalising). A strategy that works *is* mathematics — it appears in the result as structure
>   rather than as text, which is precisely what an artifact-based test cannot see. The scheme then
>   contradicts itself: v1 coded `hadwiger-conjecture-graph-theory` as `assisted` on *"central proof
>   idea … developed with the assistance of"* two models, while this cell files "suggesting
>   strategies" under `none`. Same thing, two descriptions, opposite codes.
> - **"However much work they did" overshoots.** The test is meant to be about the *kind* of
>   contribution, not the amount; as phrased it invites an agent to dismiss a large, genuinely
>   mathematical contribution because it can be filed under one of the excluded verbs. The
>   `inverse-galois-problem` recode to `none` came out right, but for the right reason — the
>   mathematics in the result, a degree-23 polynomial with Galois group M23, demonstrably came from
>   PSLQ and Magma/PARI — not because "devising computational strategies" appears on the list.
> - **`incident` is on the wrong axis.** It is defined by what happened to the *claim* (announced,
>   then withdrawn), not by what the model *produced*. Two tells: §6.1 pairs it with status
>   `progress`, so the two fields jointly encode one fact; and it emptied to zero members the moment
>   the audit changed an unrelated rule. A code that vanishes when you fix something else was never
>   a role. It also destroys information — a withdrawn AI claim was still *generated* by a model, and
>   `incident` erases whether the model wrote a proof or merely helped, which is exactly what you
>   want when studying failure.
> - **`bound` was retired on 24 September 2026** and `deep_dive.py` now rejects it, so a run emitting
>   it fails validation. It named the *kind of result* — which `status: progress` already records —
>   and so put a scope distinction on the attribution axis. The nine rows were recoded by the test
>   below; see AUDIT.md. The definition is left here unedited but **must not be used**.
> - **No code exists for an AI that criticises or referees.** The audit states this as a gap in so
>   many words. On `hopf-conjecture` an AI verifier (Refine) found a real bug under a key
>   second-order-positivity calculation in a human preprint, and the row sits in `none` *"for want of
>   anywhere better."* Note the perversity: finding an error in someone's proof has a verifiable
>   output and is often more decisive than suggesting a strategy, yet the scheme ranks it below
>   nothing. The mirror case is on `is-there-a-covering-system-with-odd-distinct-moduli`, where an AI
>   verifier passed a formalisation 7 checks out of 7 while it contained a provably false axiom.
>   Neither is counted; both are capability evidence.
> - **Wording bug in `generated`:** it says "produced the proof or counterexample" and never mentions
>   a bound or a construction, though `assisted` names both. So when `bound` was retired the audit
>   had to recode Riemann, twin primes and sphere packing to `generated` against a definition that
>   does not literally cover them. Probably part of why `bound` was invented in the first place.
>
> **The pattern:** `ai_role` is one field carrying three questions — *what did the model produce*,
> *what else was it doing that did not count*, and *did the claim survive*. Everything that works is
> an answer to the first; everything that breaks is one of the other two leaking in. The v2 proposal
> is to split it into a contribution code (`generated` / `assisted` / `none`) and a separate array
> naming the non-counting functions (`checked`, `formalised`, `refereed`, `searched_literature`,
> `wrote_prose`, `attempted_failed`) — which also retires `formalisation_only`, see the §8 note.


## On v1 §8. What to return

> **⚠ v2 NOTE — the record shape assumes one event per problem, and some problems have two.**
> `status`, `event`, `ai_role`, `resolution_direction`, `counterexample` and `credited_humans` all
> describe a single decisive event, with the instruction to put any others in prose. Where two
> events on one problem differ in who did them, the prose keeps the fact and the data loses it.
>
> **The worked example is `moving-sofa-problem`.** Two events: a July 2024 neural-network upper
> bound (2.37 → 2.3337, arXiv:2407.11106) and Baek's November 2024 claimed proof of the exact
> optimum (arXiv:2411.19826), which the record describes as purely human and not computer-assisted.
> One row, one role — so a query for *resolutions involving AI* returned a row whose resolution
> contains no AI at all. The audit found it by asking, of every AI-credited record, whether the AI's
> sources intersect the sources of the event the status rests on; across all 53, exactly this row
> and `hopf-conjecture` came back disjoint.
>
> Two rules were applied by hand and should become derivation rules rather than agent judgement:
>
> 1. **Different tiers: the furthest event wins.** Not seniority but supersession — once an exact
>    optimum near 2.2195 is proved, an upper bound of 2.3337 is not a lesser result but a dead one.
> 2. **Same tier: AI counts if AI did any of it.** Two bounds moved on a still-open problem, one by
>    a model and one by humans, neither superseding the other — the credit holds.
>
> The sofa also shows why this needs to be mechanical rather than remembered: Baek's proof is still
> `claimed` and under review at Annals. **If it fails, the furthest event reverts to the AI bound and
> the row becomes an AI one at tier `progress`** — which today requires someone to notice.
>
> The v2 proposal is an `events` array, each entry carrying its own scope, standing, date, direction
> and AI coding, with `status` derived in the pipeline by the two rules above. The derivation
> reproduces the same six status labels, so the site is unaffected. Cost is concentrated: only the
> ~194 rows that moved ever carry more than one event. **This is still under discussion.**


## On v1 §8. What to return

> **⚠ v2 NOTE — `formalisation_only` is a flag doing a code's job.** It exists because someone
> noticed that one species of excluded AI contribution was worth marking separately, and bolted on a
> boolean rather than widening the role scheme. That is the design asking for a second axis. And only
> *one* of the five excluded functions got a flag — checking, prose, strategy and criticism did not,
> which is arbitrary. Under the v2 proposal in the §6.2 note it is replaced by `formalised` as one
> member of an `ai_functions` array, alongside the others.
>
> **Two other fields are worth a second look in v2.** `confidence` came back `high` 206 / `medium`
> 251 and never `low` across all 457 records, so it is carrying almost no information — a scale
> nobody uses the bottom of is a two-value scale. And `competing_reading` was filled on all 457,
> which is good discipline, but nothing downstream reads it; if it is to earn its cost it should be
> queryable (a flag for *which axis* is in doubt) rather than prose only.
