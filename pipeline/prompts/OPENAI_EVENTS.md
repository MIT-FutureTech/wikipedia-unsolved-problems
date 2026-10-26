# Instructions

You are describing what a family of manuscripts claims about particular open problems. The manuscripts come from OpenAI's openai/math repository, a collection released on 6 October 2026 and said to have been produced by an internal OpenAI model. A study of how much recent mathematical progress involved AI measures it against a fixed list of open problems, taken from Wikipedia as it stood on 26 January 2024. An earlier pass matched this family to one or more problems on that list. Your account of each match becomes an event that a later pass judges: how much of the problem it settles, whether it is credible, and so on. You do not make those calls. You say, precisely, what the manuscripts claim.

Do not search the web. Read only the files the task lists, all of them local. You need not read every proof: read the abstract, the introduction and the statements of the main theorems, and go further only where you need to in order to say what is claimed and under what hypotheses.

## For each matched problem

The task gives you each problem's statement as the frozen list words it, and, where the research pass wrote one, its `problem_asks`: the parts the problem asks for. Write one entry per problem, saying:

- **`relevant`** — false where, having read the manuscripts, you find the family does not bear on this problem after all, with `not_relevant_because` saying why in a sentence. The matching pass was told to be generous, so this will happen. Everything else can then be left out.
- **`what_happened`** — what the manuscripts claim, in your own words, concretely: the theorem, the object constructed, the bound obtained. Name which manuscript claims what, by its title.
- **`delivers`** — what the claim establishes for this problem, with every restriction it comes with: the dimensions, the class of objects, the extra hypotheses, the special case. If the manuscripts say the result settles the problem, say so, and say whether their statement of the problem matches the list's.
- **`remains`** — which parts of the problem, or of `problem_asks`, are still open if the claim is correct.
- **`direction`** — in a few words, which way it went: proves the conjecture, disproves it, proves a case, improves a bound.
- **`object`** — where a counterexample or other explicit object is constructed, what it is and whether it is explicit; otherwise null.
- **`conditional_on`** — any unproven hypothesis the result assumes, or any other manuscript it depends on for a step it does not prove itself. Null if none.
- **`doubts`** — anything in the text itself that bears on how far to trust it: a step the authors flag as sketched, a hedge, an inconsistency between the abstract and the theorem, a claim that seems much stronger than what is proved. Null if none. Do not speculate about whether the mathematics is correct: report what the text says.
- **`readme_exception`** — the repository says that "the vast majority of results were obtained with the same procedure using an unreleased internal OpenAI model", with exceptions for "work on a zero-free region for the Riemann zeta function and proof of the Hodge Conjecture for CM abelian varieties". True if this family is one of those exceptions, otherwise false.
- **`read`** — the files you actually read.

Match on what the manuscripts claim, not on how they describe themselves. A manuscript titled as a proof of a conjecture may prove a special case of it, and one titled modestly may settle more than its title says.

## What to write

Write one JSON object to the path the task gives you, and write no other file. Every matched problem must appear exactly once.

```jsonc
{
  "family": "059",
  "entries": [
    {
      "problem": "zariski-multiplicity-conjecture",
      "relevant": true,
      "what_happened": "…",
      "delivers": "…",
      "remains": "…",
      "direction": "disproves the conjecture",
      "object": "…",
      "conditional_on": null,
      "doubts": null,
      "readme_exception": false,
      "read": ["…/build/paper.tex"]
    }
  ]
}
```
