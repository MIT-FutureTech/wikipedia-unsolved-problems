# Instructions

You are matching manuscripts to problems. OpenAI has released a collection of mathematical manuscripts, grouped into result families. A fixed list of 457 open problems, taken from Wikipedia's *List of unsolved problems in mathematics* as it stood on 26 January 2024, is the denominator of a study of how much recent mathematical progress involved AI. Your task is to say, for each family you are given, which of those problems it bears on.

You are not judging whether the mathematics is right, how far it goes, or whether it counts. Later passes read each matched manuscript in full and decide all of that. A family you fail to match is never looked at again, while a match that turns out to be wrong costs one later pass a few minutes. **So when in doubt, match.**

Do not search the web or open anything. Everything you need is in the message: the families, and the full list of problems.

## What counts as bearing on a problem

A family bears on a problem when a reader who knows the problem would want to see the family before saying what has happened to it. That includes a family that:

- claims to settle the problem, prove it or disprove it;
- settles a case of it: a dimension, a class of objects, one of several parts the problem asks about;
- moves a bound or a quantity the problem asks about;
- settles a variant: an analogue, a weaker or stronger form, the same question under different hypotheses, a local or conditional version;
- is about the problem under a different name. Many problems are known by several names, and a family may name the person while the list names the object, or the other way round.

Match on the mathematics, not the words. A family on "Littlewood polynomials" does not bear on the Littlewood conjecture about Diophantine approximation, though they share a name. A family on Ostmann's inverse Goldbach problem is a different problem from Goldbach's conjecture, but close enough to be worth a later look, so match it as a variant.

A family can bear on several problems, and a problem can be matched by several families. Both are common: a list entry that names a whole area, such as the homological conjectures in commutative algebra, may be matched by several families, each settling one of the conjectures in it.

## The hints

Some families come with **name hints**: problems whose distinctive words appear in the family's title or summary. They were found mechanically and are often wrong (a shared word such as "regular" or "perfect" means nothing). Use them as a prompt to consider a problem, never as a reason to match it. Where you decide a hinted problem does not bear on the family, you need not say so.

## What to write

Write one JSON object to the path the task gives you, and write no other file. Every family you were given must appear exactly once, in the order given, including the ones that match nothing.

```jsonc
{
  "batch": 7,                                   // as the task gives it
  "families": [
    {
      "family": "059",                          // as given
      "matches": [
        {
          "problem": "zariski-multiplicity-conjecture",   // a key from the list, exactly as written
          "relation": "settles",                // settles | case | bound | variant | other — your best guess
          "why": "Constructs ambiently homeomorphic hypersurface germs of different multiplicity, which is a counterexample to the conjecture as stated."
        }
      ]
    },
    {
      "family": "060",
      "matches": []                             // nothing on the list: say so with an empty list
    }
  ]
}
```

`relation` is a hint for the passes that follow, not a ruling: `settles` claims the whole problem either way, `case` a restricted part of it, `bound` a quantity it asks about, `variant` a changed version of the question, and `other` anything else worth a look. `why` is one sentence, in your own words, saying what in the family touches the problem.
