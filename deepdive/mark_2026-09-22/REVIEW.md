# Records to review by hand

Five of the 457 records in this trial carry an internal contradiction. None of them block the
build — they are valid JSON with valid codes, so `merge_research.py` will ingest them and the
wrong value simply lands in the dataset. Fix them in `out/<key>.json` whenever convenient, and
re-run the contradiction scan afterwards.

| key | problem | what to change |
|---|---|---|
| `borsuks-problem` | `counterexample.is_counterexample` is true but `resolution_direction` is `confirmed`. The result lowers the known counterexample dimension from 64 to 63 — it goes *against* the conjecture. | `resolution_direction` → `refuted` |
| `is-there-a-non-terminating-game-of-beggar-my-neighbour` | Same shape: an exhibited counterexample coded `confirmed`. | `resolution_direction` → `refuted` |
| `harborths-conjecture` | `event.date` is `2024` (year precision) but `predates_frozen_revision` is false. The snapshot is 26 Jan 2024, so a year-only 2024 date cannot settle which side of the line it falls on. | establish the month, or say in `summary` that the side is undetermined |
| `spherical-bernsteins-problem` | `status` is `open_stale` but `predates_frozen_revision` is false — the two disagree about whether the event predates the snapshot. | make them agree; `open_stale` requires a pre-snapshot event |
| `guralnick-thompson-conjecture` | `no_change_found` is true with `status: open_stale`. `no_change_found` means nothing was found at all, which contradicts recording a pre-snapshot resolution. | `no_change_found` → false |

The first two are the reason to add a rule to DEEP_DIVE.md §6.4: **an explicit counterexample forces
`resolution_direction` to `refuted` or `mixed`, never `confirmed`.** That rule is not in the
document yet, so any future run can reproduce these.

## Corrected by hand, 24 September 2026

Two records rested on an event dated *before* the frozen revision while carrying a status that
asserts movement since it. Both were **changed by hand by a human reviewer** — not by the
researching agent and not by any automated pass — and each carries a `corrections` entry saying so.

| key | problem | change |
|---|---|---|
| `novikov-conjecture` | Event is arXiv:2310.01219, 2 October 2023, three months before the snapshot. | `status` `partial` → `open` |
| `gaussian-moat-problem` | Event is arXiv:2401.08441, submitted 16 January 2024 and withdrawn by its author that week — ten days before the snapshot, and retracted besides. | `status` `progress` → `open` |

`open_stale` was not used for either: it is for a pre-snapshot **resolution** the list never caught
up with, and neither of these resolves anything. A pre-snapshot partial result or withdrawn claim
is a note on a problem that is still open, which is what the site's own About tab already says.

The Gaussian moat row was the more damaging of the two. January 2024 is the first month on the
site's time axis, so unlike Novikov — which fell outside the axis and was silently dropped — it was
being drawn on the cumulative progress chart as though it were an advance inside the window.

**`novikov-conjecture` may need reversing.** The agent's own `competing_reading` notes that if the
diffeomorphism-group generalization was only fully established in the August 2024 or February 2025
revision rather than in v1, the event belongs inside the window and the record should return to
`partial`. Nobody has compared the arXiv versions. That comparison is the one piece of work that
would settle it.

These two are the reason for the new validator rule in `deep_dive.py`: **`predates_frozen_revision:
true` requires `status` to be `open_stale` or `open`.** The existing consistency scan checked for an
`open_stale` carrying a post-snapshot event but never the converse, which is why both survived it.

## Withdrawn claims, corrected by hand, 24 September 2026

Five more records rested on an AI claim that had been announced and then withdrawn. All five were
**changed by hand by a human reviewer** — not by the researching agent and not by any automated
pass — and each carries a `corrections` entry stating the change, the reasoning, and that a human
made it.

These corrections **override DEEP_DIVE.md §6.1**, which directs that a withdrawn AI claim be
recorded as `progress` with `ai_role: incident`. Every agent followed that instruction correctly.
The instructions are deliberately left unedited, so these records and the document they were
produced under now disagree on this point, and the `corrections` entries are the reason why.

The rule applied instead: *a withdrawn claim leaves the problem exactly where it was, so it is not
the event the status rests on. Discard it, take the furthest genuine event that remains, and let
`status` and `ai_role` both follow that.*

| key | change | what remained after discarding the withdrawn claim |
|---|---|---|
| `inscribed-square-problem` | `event` re-pointed to arXiv:2407.07798; `ai_role` `incident` → `none`; status stays `progress` | Greene–Lobb moved a Lipschitz threshold on a restricted case, with no AI claimed — already described in this same record |
| `collatz-conjecture` | `status` `progress` → `open`; `ai_role` → `none` | Nothing qualifying. Verification to 2^71 is one more example of a universal claim; the density-bound improvement rests only on the claimant's own repository |
| `is-there-a-covering-system-with-odd-distinct-moduli` | `status` `progress` → `open`; `ai_role` → `none` | Nothing. Mian–Siddique formalise an already-known folklore bound, which moves no mathematics and is `none` under §6.2 |
| `do-siegel-zeros-exist` | `status` `progress` → `open`; `ai_role` → `none` | Nothing |
| `yang-mills-existence-and-mass-gap` | `status` `progress` → `open`; `ai_role` → `none` | Nothing |

Named systems stay in `ai.systems` on every one of these as evidence of what happened; they are no
longer counted as credited models, which is the existing convention for `ai_role: none` records.

**No record now carries `ai_role: incident`.** That is a consequence of the rule, not a goal. A
future run following §6.1 as written will repopulate the category.

The five JSON files were rewritten programmatically when these entries were added, which dropped
the blank lines the archive uses between sections. Indentation was restored to match; the blank
lines were not. No field other than those named above was altered.

## Two codes that did not match their own record, corrected by hand, 24 September 2026

Unlike the withdrawn-claim group above, **neither of these departs from the instructions** — each
applies a rule as written, where the original coding did not.

| key | change | why |
|---|---|---|
| `inverse-galois-problem` | `ai_role` `assisted` → `none` | The authors' disclosure is almost entirely activity §6.2 excludes by name, bracketed by "No text in this article was written by AI" and "Our final results were verified in Magma and PARI/GP without the use of AI." The Carathéodory pattern, which the §3 fix missed. `status` stays `partial` |
| `sphere-packing` | `status` `claimed` → `progress`, `ai_role` `generated` → `bound`, `resolution_direction` → null | The record's own first sentence says the problem remains open, and its `competing_reading` argues for `progress`. Astra determined the exact asymptotic exponent of the Cohn–Elkies *linear-programming bound* — a theorem about how far a proof method can reach, not about packing density. §6.2: `bound` "is not a weak `generated`" |

Together these take resolutions from 59 to 58 and AI-involved resolutions from 26 to 25.

## Claims not credible enough to count, corrected by hand, 24 September 2026

Nine `claimed` records rested on a preprint that is very unlikely to be a proof, though nothing has
knocked it down. The correction was **directed by a human reviewer (Alex Fogelson) and drafted by
Claude (claude-opus-5-5)** from each record's own findings; no new sources were opened. Like the
withdrawn-claim group, these **override DEEP_DIVE.md §6.1**: the claim is set aside and the furthest
genuine event that remains sets the status. The reasoning for each is in AUDIT.md §4 and in the
record's own `corrections` entry.

| key | change |
|---|---|
| `montgomerys-pair-correlation-conjecture` | `status` `claimed` → `open`; `resolution_direction` → null |
| `values-of-g-k-and-g-k-in-warings-problem` | `status` `claimed` → `open`; `resolution_direction` → null |
| `cherns-conjecture-affine-geometry` | `status` `claimed` → `open`; `resolution_direction` → null |
| `hermites-problem` | `status` `claimed` → `open`; `resolution_direction` → null |
| `littlewood-conjecture` | `status` `claimed` → `open`; `resolution_direction` → null |
| `yaus-conjecture-on-the-first-eigenvalue` | `status` `claimed` → `progress`; `event` re-pointed to arXiv:2606.10962; `resolution_direction` → null |
| `albertson-conjecture` | `status` `claimed` → `partial`; `event` re-pointed to Cranston, arXiv:2512.08020 |
| `abc-conjecture` | `status` `claimed` → `progress`; `event` re-pointed to arXiv:2410.12234 (exceptional-set bound); `resolution_direction` → null |
| `whitehead-conjecture` | `status` `claimed` → `open`; `resolution_direction` → null |

The re-pointed records prefix `outcome` with the new event and keep the agent's original text
after it. These nine were edited in place, so unlike the earlier batches their blank lines survive.

`build.py` now carries every `corrections` entry through to the flat outputs: `hand_corrected` and
`corrected_fields` columns in the CSV and SQLite `problems` table (a retention, `from` = `to`, does
not set the flag), and a `problem_corrections` table in SQLite holding each entry in full.

## `bound` retired as an AI role, 24 September 2026

Directed by the reviewer (Alex Fogelson), drafted by Claude (claude-opus-5-5). `bound` described
the kind of result, which `status` records, not who did the work. The nine `bound` records were
recoded by the §6.2 test — `riemann-hypothesis`, `twin-prime-conjecture`, `sphere-packing` and
`hadamards-maximal-determinant-problem` to `generated`; `hadwiger-conjecture-graph-theory`,
`erdos-gyarfas-conjecture`, `conways-99-graph-problem` and `resolution-of-singularities` to
`assisted`; `moving-sofa-problem` to `none`. Reasoning per record is in AUDIT.md §4 and in each
`corrections` entry. `deep_dive.py` now rejects `bound`; DEEP_DIVE.md §6.2 still defines it.

## Claimed rows that were never claimed resolutions, 24 September 2026

Directed by the reviewer (Alex Fogelson), drafted by Claude (claude-opus-5-5). Every `claimed` row
was checked for scope (does it claim the whole problem?) and credibility. Agents had coded
unreviewed special cases and bounds as `claimed`, which counted them as resolutions. Full table and
reasoning in AUDIT.md §4; each record carries its own `corrections` entry.

| change | keys |
|---|---|
| `claimed` → `partial` | `birch-and-swinnerton-dyer-conjecture`, `tate-conjecture`, `cartan-hadamard-conjecture`, `big-line-big-clique-conjecture`, `values-of-the-hermite-constants-for-dimensions-other-than`, `rysers-conjecture`, `tuzas-conjecture`, `arnold-givental-conjecture`, `arthurs-conjectures`, `is-the-borel-monadic-theory-of-the-real-order`, `hopf-conjecture`, `fugledes-conjecture`, `rendezvous-problem`, `fontaine-mazur-conjecture` (event re-pointed to Thorne) |
| `claimed` → `progress`, direction → null | `borsuks-problem`, `degree-diameter-problem`, `find-the-value-of-the-de-bruijn-newman-constant`, `universal-point-set`, `1-3-2-3-conjecture` (event re-pointed to Aires–Kahn, `ai_role` → `none`) |
| `claimed` → `open`, `ai_role` → `none` | `are-gamma-the-euler-mascheroni-constant-pi-e-pi` (Sun's proof knocked down by Wachs) |
| retained with doubt (`from` = `to`) | `casas-alvero-conjecture`, `buchis-problem`, `mean-value-problem`, `ibragimov-iosifescu-conjecture-for-mixing-sequences`, `does-there-exist-an-o-minimal-first-order-theory-with` |

Resolutions 49 → 29. `explorer_app.js` now labels direction by status ("Case proved" on partial
rows, nothing on progress) and no longer prints `outcome` prose inside the status badge.

**Still to fix:** `novikov-conjecture` is `open` but kept `resolution_direction: confirmed` from
before its earlier correction.
