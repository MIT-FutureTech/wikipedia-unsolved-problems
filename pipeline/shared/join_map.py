"""How a research record's slug finds its row in build.py.

The join is on the problem's statement text, not on a name: both sides run the frozen bullet
through wikitext.strip_wiki, so the strings are equal by construction. 457 of the 462 slugs match
that way with nothing to maintain.

The five below are the exception. They are the Millennium Prize Problems, which the page names in
its introduction rather than in a field list, so build.py adds them as records of its own with a
hand-written description instead of a bullet. They join on build's record name instead.

If a statement ever stops matching, merge_research.py says so by name — add it here rather than
loosening the match.
"""

BY_NAME = {
    'birch-and-swinnerton-dyer-conjecture': 'Birch and Swinnerton-Dyer conjecture',
    'hodge-conjecture':                     'Hodge conjecture',
    'navier-stokes-existence-and-smoothness': 'Navier–Stokes existence and smoothness',
    'p-versus-np-problem':                  'P versus NP problem',
    'yang-mills-existence-and-mass-gap':    'Yang–Mills existence and mass gap',
}
