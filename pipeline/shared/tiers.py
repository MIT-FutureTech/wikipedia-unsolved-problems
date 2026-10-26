"""JUDGE.md §3 steps 1-2: which tier an answered event earns, if any.

One definition, shared by the judge (which derives a problem's codes from it) and the merge (which
hands each event's tier to the site, where every chart applies its own rule to the events).
"""
DISCARD_SCOPE = ('instances', 'variant', 'none')
DISCARD_CREDIBILITY = ('not_credible', 'knocked_down')
TIERS = ('progress', 'partial', 'claimed', 'resolved')      # ascending, for §3 step 3


def tier_of(row):
    """The tier an answered event earns, or None where step 1 discards it."""
    if row.get('scope') in DISCARD_SCOPE or row.get('credibility') in DISCARD_CREDIBILITY:
        return None
    scope, verified = row.get('scope'), row.get('verification')
    if scope == 'whole':
        return 'resolved' if verified in ('digested', 'checkable') else 'claimed'
    return {'case': 'partial', 'bound': 'progress'}.get(scope)
