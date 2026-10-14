import argparse, re, json, csv, sqlite3, html, os, sys, datetime
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest
RESEARCH = None      # loaded below, once DATA_DIR is known

# Dataset version. Every input and output lives in data/<VERSION>/; this is the pointer to move
# when a new version is produced. The script can be run from any working directory.
_ap = argparse.ArgumentParser()
_ap.add_argument('--version', required=True, metavar='NAME',
                 help='the dataset version to work in: data/<NAME>/ — e.g. mark_2026-09-22')
_ap.add_argument('--site-dir', metavar='DIR',
                 help='write data.js and the page here instead of site/, e.g. to preview a trial '
                      'without touching the published files; the page sources are still read from site/')
_args = _ap.parse_args()
VERSION = _args.version
STARTED = manifest.now()
# The agent pass wrote its records 22-24 Sep 2026; the last hand corrections landed 28 Sep. This is
# the later date, so it is the date every status on the site was last reviewed.
STATUS_CHECKED = '2026-09-28'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, 'data', VERSION)
P = lambda name: os.path.join(DATA_DIR, name)

# The research: one record per problem from pipeline/stage_2_research_each_problem/deep_dive.py, merged and normalised by
# pipeline/stage_6_merge_and_date_the_models/merge_research.py. Keyed by statement text, with the five Millennium problems keyed by
# build's own record name (see pipeline/shared/join_map.py).
if not os.path.exists(P('research.json')):
    raise SystemExit('no research.json — run pipeline/stage_6_merge_and_date_the_models/merge_research.py first')
RESEARCH = json.load(open(P('research.json'), encoding='utf-8'))
S_BY_STATEMENT, S_BY_NAME = RESEARCH['by_statement'], RESEARCH['by_name']
# Bullets the article uses as headings for the problems beneath them — not problems, and not
# researched. They stay in the dataset flagged, so the page's 467 bullets still reconcile, but
# they are excluded from every count and from the site.
GROUPINGS = set(RESEARCH.get('groupings') or [])
MODELS = RESEARCH['models']
# An unversioned name ("Claude", "ChatGPT") has no release of its own: the date the release pass
# found is the product line's launch, not the model used, so it is dropped rather than plotted.
from model_aliases import UNVERSIONED
for m in UNVERSIONED & MODELS.keys():
    MODELS[m].update(release=None, preview_date=None, available=None, inherited_from=None, release_basis='unversioned')

from wikitext import LINK_RE, MATH_RE, links_of, strip_wiki, first_link

SRC = open(P('page.wiki'), encoding='utf-8').read()
SRC = SRC[:SRC.index('== See also ==')]

REV = dict(revid=1199136318, timestamp='2024-01-26T03:23:06Z', user='Beland',
           url='https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=1199136318')

MILLENNIUM = {'Birch and Swinnerton-Dyer conjecture', 'Hodge conjecture', 'Navier–Stokes existence and smoothness',
              'P versus NP problem', 'Riemann hypothesis', 'Yang–Mills existence and mass gap'}
SMALE = {'Riemann hypothesis': 1, 'Jacobian conjecture': 16, 'mean value problem': 4, "Hilbert's sixteenth problem": 13}
LANDAU = {'Goldbach conjecture', "Legendre's conjecture", 'Twin prime'}


def split_name(body, clean):
    fl = first_link(body)
    if fl:
        title, disp, rest = fl
        rest_c = strip_wiki(rest)
        # extend name if the link is a person / partial name (e.g. "[[Banach]]'s problem", "[[Birkhoff]] conjecture")
        m = re.match(r"^((?:'s)?\s*(?:conjectures?|problem|hypothesis|multiple mixing problem)\b)(.*)$", rest_c, re.S)
        if m and len(disp.split()) <= 3:
            g = m.group(1).strip()
            disp = disp + g if g.startswith("'") else disp + ' ' + g
            rest_c = m.group(2)
        m2 = re.match(r"^\s*(?:conjecture\s*)?[:–—-]\s*(.*)$", rest_c, re.S) or re.match(r"^\s*(?:,\s*)?(.*)$", rest_c, re.S)
        desc = m2.group(1).strip() if m2 else rest_c
        desc = re.sub(r'^(?:\(|–|-|—|,)\s*', '', desc).strip()
        return disp.strip(), desc
    # unlinked start: "Name: desc" / "Name on desc" / question
    m = re.match(r"^(.{3,70}?(?:conjecture|problem|hypothesis|Notebook))\s*:\s*(.*)$", clean, re.S)
    if m:
        return re.sub(r'^[Tt]he\s+', '', m.group(1)).strip(), m.group(2).strip()
    m = re.match(r"^(.{3,70}?(?:conjecture|problem|hypothesis|Notebook))\s*(?:[:–—-]\s*|,\s*|\s+(?=on\b|that\b|concerning\b|relating\b|in\b|for\b))(.*)$", clean, re.S)
    if m and not clean.rstrip().endswith('?'):
        return re.sub(r'^[Tt]he\s+', '', m.group(1)).strip(), m.group(2).strip()
    return clean, ''


def classify(name, clean):
    t = (name + ' ' + clean).lower()
    nl = name.lower()
    if 'conjecture' in nl or 'hypothesis' in nl: return 'conjecture'
    if 'problem' in nl: return 'problem'
    if clean.strip().endswith('?') or re.match(r'^(is|are|do|does|can|what|which|for which|how|if|without|give|find|determine|characteri|classify|solving|improving|assume)\b', clean.lower()):
        return 'question'
    if 'conjecture' in t or 'hypothesis' in t:
        return 'conjecture'
    if 'problem' in t:
        return 'problem'
    if re.match(r'^(the values? of|regularity|convergence|existence|finding|resolution)', clean.lower()):
        return 'computation/other'
    return 'other'


def named_after(name):
    n = re.sub(r"^(The|the)\s+", '', name)
    m = re.match(r"^((?:[A-ZÀ-Ž][\w'’.\-]*(?:\s+(?:de|von|van|der|and|&)\s+)?\s*)(?:[–\-,]\s*(?:and\s+)?[A-ZÀ-Ž][\w'’.\-]*\s*)*)(?:'s|’s)?\s+(?:[a-z0-9/^\-]+\s+)*(conjectures?|problems?|hypothesis|constants?|numbers?|primes?|sequence|equations?|series|theorem|question|moat|notebook|set|group|graph)\b", n)
    if not m:
        return []
    people = re.split(r"\s*[–,]\s*(?:and\s+)?|\s+and\s+", m.group(1).replace("'s", '').replace('’s', ''))
    people = [p.strip(" .'") for p in people if p.strip(" .'")]
    # Deny-list of leading words that are not surnames. There used to be a second, longer copy of
    # this set assigned to a local `bad` immediately above and never read — removed 2026-09-19;
    # the set below is the one that has always been in force, so nothing in the output moved.
    return [p for p in people if p and p.split()[0] not in {'Are', 'Is', 'Does', 'Do', 'What', 'Which', 'How', 'Can', 'The', 'For', 'Find', 'Give',
            'Determine', 'Existence', 'Convex', 'Uniform', 'Generalized', 'Grand', 'Regularity', 'Convergence', 'Problems', 'Improving',
            'Solving', 'Resolution', 'Standard', 'Homological', 'Finite', 'Invariant', 'Inscribed', 'Congruent', 'Minimum', 'Class', 'Odd',
            'Perfect', 'Sphere', 'Square', 'Sum', 'Sums', 'Tripod', 'Unit', 'Universal', 'Word', 'Second', 'Implicit', 'Unknotting', 'Volume',
            'Section', 'Determinantal', 'Monomial', 'Wild', 'Abundance', 'General', 'Big', 'Closed', 'Filling', 'Spherical', 'Happy',
            'Covering', 'Circle', 'Kissing', 'Moving', 'Lonely', 'Map', 'No', 'Rendezvous', 'Degree', 'Cycle', 'Linear', 'List', 'Total',
            'Overfull', 'Main', 'Stable', 'Twin', 'New', 'Additive', 'Mean', 'Quantum', 'Special', 'Restricted', 'Exponent', 'Gaussian',
            'Prime', 'Telescope', 'Sunflower', 'MLC', 'GNRS', 'Opaque', 'Earth', 'Dissection', 'Borromean', 'Analytic', 'Flint', 'Density',
            'Rupert', 'Balanced', 'Cluster', 'Cousin', 'Palindromic', 'Regular', 'Safe', 'Sexy', 'Carol', 'Kynea', 'Grundy', 'Octal', 'Fortunate'}]


records, solved, placed = [], [], set()
h2 = h3 = h4 = None
mode = None
parent_stack = {}
for raw in SRC.split('\n'):
    line = raw.rstrip()
    hm = re.match(r'^(=+)\s*(.*?)\s*=+$', line)
    if hm:
        lvl, title = len(hm.group(1)), hm.group(2)
        if lvl == 2:
            h2, h3, h4 = title, None, None
            mode = 'unsolved' if title == 'Unsolved problems' else ('solved' if title.startswith('Problems solved') else None)
        elif lvl == 3:
            h3, h4 = title, None
        else:
            h4 = title
        continue
    bm = re.match(r'^(\*+)\s*(.*)$', line)
    if not bm or mode is None:
        continue
    depth, body = len(bm.group(1)), bm.group(2)
    clean = strip_wiki(body)
    wl = links_of(body)
    if mode == 'solved':
        ym = re.search(r'\(([^()]*?(?:\([^()]*\)[^()]*)*?)(?:,\s*|\s+)(?:series of preprints in\s*)?(\d{4})(?:[–-]\d{4})?\)', clean)
        year = int(ym.group(2)) if ym else None
        # drop years embedded in the solver list ("Reiher, 2003, di Fiore, 2003")
        solvers = re.sub(r',?\s*\b(?:19|20)\d{2}\b', '', re.sub(r'\s+', ' ', ym.group(1))).strip(' ,') if ym else ''
        fl = first_link(body)
        name = fl[1] if fl else re.split(r'\s\(', clean)[0]
        name = re.sub(r'^(The|the)\s+', '', name).strip()
        solved.append(dict(name=name, field=h3, decade_section=h4, year_solved=year, solved_by=solvers,
                           disproof=clean.lower().startswith('disproof'),
                           wikipedia_url=('https://en.wikipedia.org/wiki/' + wl[0].replace(' ', '_')) if wl else None,
                           wikilinks=wl, statement=clean))
        continue
    name, desc = split_name(body, clean)
    name = name.rstrip(':').strip()
    if name.startswith('The universality problem'): name, desc = 'universality problem for C-free graphs', clean.split(': ',1)[1]
    if name == "Woodin's": name = "Woodin's Ω-conjecture"
    if name == 'How many unit distances': name, desc = clean, ''  # the opening link's display text is a sentence fragment
    fl = first_link(body)
    primary = fl[0] if fl else None
    key = primary or name
    # year_introduced is not researched in this version (merge_research.year_introduced is a stub),
    # so every record starts with no year; the join below fills it if a record ever carries one.
    yinfo = (None, None, '')
    field, sub = h3, h4
    if field == 'Number theory' and sub == 'General':
        sub = None
    rec = dict(
        id=len(records) + 1,
        name=name,
        description=desc if desc else clean,
        statement=clean,
        field=field,
        subfield=sub,
        type=classify(name, clean),
        year_introduced=yinfo[0],
        year_source={'wp': 'Wikipedia article lead', 'lit': 'mathematical literature (recalled)', None: None}[yinfo[1]],
        year_note=yinfo[2],
        year_approx=False,
        named_after=named_after(name),
        primary_wikilink=primary,
        wikipedia_url=('https://en.wikipedia.org/wiki/' + (primary or (wl[0] if wl else '')).replace(' ', '_')) if (primary or wl) else None,
        wikilinks=wl,
        n_wikilinks=len(wl),
        list_depth=depth,
        parent=parent_stack.get(depth - 1) if depth > 1 else None,
        millennium_prize=(primary in MILLENNIUM) or name in MILLENNIUM,
        hilbert_problem=(lambda m: {'ninth': 9, 'tenth': 10, 'eleventh': 11, 'twelfth': 12, 'fifteenth': 15, 'sixteenth': 16}[m.group(1)] if m else None)(re.search(r"Hilbert's (ninth|tenth|eleventh|twelfth|fifteenth|sixteenth) problem", clean)),
        smale_problem=SMALE.get(primary or name),
        landau_problem=(primary in LANDAU) or ('n^{2} + 1' in clean and 'primes of the form' in clean),
        has_formula='$' in clean,
        source_revision=REV['revid'],
    )
    parent_stack[depth] = rec['name']
    records.append(rec)

# also register the six Millennium problems (listed in the page intro, not in the field lists) as their own records
MILL = [("Birch and Swinnerton-Dyer conjecture", "Number theory", 1965, "Birch & Swinnerton-Dyer, 1965", "Relates the rank of the group of rational points on an elliptic curve to the order of vanishing of its L-function at s=1.", ['Birch', 'Swinnerton-Dyer']),
        ("Hodge conjecture", "Geometry", 1950, "Hodge, ICM 1950", "Every Hodge class on a projective complex manifold is a rational combination of classes of algebraic cycles.", ['Hodge']),
        ("Navier–Stokes existence and smoothness", "Analysis", 1822, "Navier 1822, Stokes 1845; Clay formulation 2000", "Do smooth, globally defined solutions of the 3D Navier–Stokes equations always exist for smooth initial data?", ['Navier', 'Stokes']),
        ("P versus NP problem", "Theoretical computer science", 1971, "Cook 1971 (Levin 1973)", "Can every problem whose solution can be verified quickly also be solved quickly?", []),
        ("Yang–Mills existence and mass gap", "Mathematical physics", 1954, "Yang & Mills 1954; Clay formulation 2000", "Prove that quantum Yang–Mills theory exists on R^4 and has a positive mass gap.", ['Yang', 'Mills'])]
for nm, fld, yr, note, desc, ppl in MILL:
    records.append(dict(id=len(records) + 1, name=nm, description=desc, statement=desc, field=fld, subfield='Millennium Prize Problems',
                        type='conjecture' if 'conjecture' in nm else 'problem', year_introduced=yr, year_source='mathematical literature (recalled)',
                        year_note=note, named_after=ppl, primary_wikilink=nm, wikipedia_url='https://en.wikipedia.org/wiki/' + nm.replace(' ', '_'),
                        wikilinks=[nm], n_wikilinks=1, list_depth=1, parent=None, millennium_prize=True, hilbert_problem=8 if 'Riemann' in nm else None,
                        smale_problem=3 if nm.startswith('P versus') else None, landau_problem=False, has_formula=False, source_revision=REV['revid']))
# Riemann hypothesis is in the number-theory list already; flag it
for r in records:
    if r['name'] == 'Riemann hypothesis':
        r['millennium_prize'] = True; r['hilbert_problem'] = 8; r['smale_problem'] = 1
    if r['primary_wikilink'] == 'Generalized Poincaré conjecture':
        r['millennium_prize'] = False


def predates(st):
    """Did this result appear before a model credited on it was available to anyone?

    Compared against `available` — the private preview where a system had one, otherwise the
    public release — because a system its users could reach was available then, whatever month it
    later reached general availability. True when the result predates ANY credited model: that is
    the surprising case, a result produced with something the public could not yet use.

    Compared at the precision the event carries: a year-only date is only counted as earlier when
    the whole year is earlier, so the flag never rests on a month nobody sourced.
    """
    when = st.get('month') or (str(st['year']) if st.get('year') else None)
    if not when:
        return None, []
    hits = []
    for m in st['ai_models']:
        avail = (MODELS.get(m) or {}).get('available')
        if not avail:
            continue
        n = min(len(when), len(avail))
        if when[:n] < avail[:n]:
            hits.append(m)
    return bool(hits), hits


# Models come from research.json, which merge_research.py builds from pipeline/shared/model_aliases.py:
# the canonical name each source string maps to, with lab, family, kind and release date. Release
# dates are not researched in this version — they are a pass of their own — so `release` is None
# throughout and the site shows no release timeline until that pass runs.
MODEL_FAMILY = {m: v.get('family') for m, v in MODELS.items()}
LAB_OF_MODEL = {m: v.get('lab') for m, v in MODELS.items()}

STATUS_LABEL = {'open': 'Open', 'resolved': 'Resolved', 'partial': 'Partially resolved', 'claimed': 'Resolution claimed', 'progress': 'Notable progress', 'open_stale': 'Already settled before snapshot'}
used = set()
for r in records:
    r['is_grouping'] = r['statement'] in GROUPINGS
    st = S_BY_STATEMENT.get(r['statement']) or S_BY_NAME.get(r['name'])
    r['ai_models'], r['ai_model_families'], r['ai_labs'] = [], [], []
    if st:
        placed.add(st['key'])
        r.update(status=st['status'], status_label=STATUS_LABEL[st['status']], outcome=st['outcome'],
                 year_resolved=st['year'], resolved_by=st['by'], ai_involvement=st['ai'],
                 ai_systems=st['ai_systems'], ai_system='; '.join(st['ai_systems']) or None,
                 status_note=st['note'], status_sources=st['sources'],
                 resolution_direction=st['direction'], research_key=st['key'],
                 confidence=st['confidence'], counterexample=st['counterexample'],
                 corrections=st.get('corrections') or [],
                 # Each surviving event with the judge's answers: the site's charts apply their own
                 # rules to these (merge_research.py, events_of), rather than to the one status.
                 events=st.get('events') or [])
        r['ai_models'] = st['ai_models']
        r['predates_availability'], r['predates_models'] = predates(st)
        r['ai_model_families'] = sorted({MODEL_FAMILY[m] for m in st['ai_models'] if MODEL_FAMILY.get(m)})
        r['ai_labs'] = st['ai_labs']
        r['month_resolved'] = st['month']
        r['month_approx'] = False
        yi = st.get('year_introduced') or (None, None, '', False)
        if yi[0]:
            r['year_introduced'], r['year_source'], r['year_note'] = yi[0], yi[1], yi[2]
            r['year_approx'] = bool(yi[3]) if len(yi) > 3 else False
    else:
        r.update(status='open', status_label='Open', outcome=None, year_resolved=None, resolved_by=None,
                 ai_involvement='none', ai_systems=[], ai_system=None, status_note='', status_sources=[],
                 resolution_direction=None, research_key=None, confidence=None, counterexample=False,
                 corrections=[], month_resolved=None, month_approx=False,
                 predates_availability=None, predates_models=[], events=[])
    # A correction whose `from` equals its `to` records a reviewed-and-retained call, not a change.
    # Corrections by the judging pass are an automated model's, not a human's, so they are flagged apart.
    real = [c for c in r['corrections'] if c.get('from') != c.get('to')]
    by_judge = lambda c: (c.get('by') or '').startswith('judging pass')
    changed = [c['field'] for c in real]
    r['hand_corrected'] = any(not by_judge(c) for c in real)
    r['judge_corrected'] = any(by_judge(c) for c in real)
    r['corrected_fields'] = '; '.join(dict.fromkeys(changed)) or None
unplaced =sorted({v['key'] for v in list(S_BY_STATEMENT.values()) + list(S_BY_NAME.values())} - placed)
if unplaced: print('RESEARCH RECORDS THAT MATCHED NO BULLET:', unplaced)
from collections import Counter

# pipeline/stage_1_fetch_the_frozen_list/fetch_article_history.py reports, for each opening wikilink, what stood at that title on the snapshot
# date: an article, a redirect, or nothing. Two hand lists refine that raw answer, and both are
# reviews done for this run — see AUDIT.md §2 for how they were built and how many titles each
# covers.
#
# PAGE_ALIAS: titles that were redirects in Jan 2024 but whose target is the problem itself — a
# rename, a hyphenation, or the problem's object. The problem did have a dedicated article, under
# another title, so these count as own_page_2024.
PAGE_ALIAS = {
    # Reviewed by hand on 19 Sep 2026 over all 34 titles that were redirects on the snapshot date.
    # These 20 redirect to the problem itself under another name — a rename, a hyphenation, a
    # singular/plural, or the problem's own object — so the problem did have a dedicated article.
    # The other 14 land in a broader topic, a related-but-different problem, or a biography
    # (Deligne conjecture -> Pierre Deligne), and are left classified 'broader'.
    "Beal's conjecture",                     # -> Beal conjecture
    'Congruent number problem',              # -> congruent number
    "Conway's thrackle conjecture",          # -> Thrackle: the conjecture is that article's subject
    'Generalized star height problem',       # -> Generalized star-height problem (hyphenation)
    'Gilbert–Pollack conjecture on the Steiner ratio of the Euclidean plane',  # -> Gilbert–Pollack conjecture
    'Goldbach conjecture',                   # -> Goldbach's conjecture
    'Kakeya conjecture',                     # -> Kakeya set: the problem's object
    "Negami's conjecture",                   # -> Planar cover: the conjecture is that article's open question
    'Opaque forest problem',                 # -> Opaque set
    'Outer billiard',                        # -> Outer billiards (plural)
    'Problems in loop theory and quasigroup theory',  # -> List of problems in loop theory and quasigroup theory
    'Ravenel conjectures',                   # -> Ravenel's conjectures
    "Reinhardt's conjecture",                # -> Smoothed octagon: the problem's object
    'Square packing in a square',            # -> Square packing
    'Standard conjectures',                  # -> Standard conjectures on algebraic cycles
    'cycle double cover conjecture',         # -> Cycle double cover
    'implicit graph conjecture',             # -> Implicit graph: the conjecture is that article's open question
    'kissing number problem',                # -> Kissing number
    'list coloring conjecture',              # -> List edge-coloring
    'total coloring conjecture',             # -> Total coloring
}

# PAGE_BROADER: titles that were articles in Jan 2024 but are not about the problem — a biography
# the bullet links for the person's name, a section header of the list itself, or a broader topic
# of which the problem is one paragraph. These do not count as the problem having its own page.
PAGE_BROADER = {
    # Reviewed by hand on 19 Sep 2026 over all 262 opening links that stood as articles on the
    # snapshot date. Three kinds, and none of them is the problem's own page.
    #
    # Biographies — the bullet links the person because the problem carries their name. Found by
    # checking every one of the 262 for a births/deaths/living-people category, which caught three
    # that a lead-sentence regex had missed.
    'Alexandre Eremenko', 'George David Birkhoff', 'Grigory Margulis', 'Hillel Furstenberg',
    'Stefan Banach', 'Vladimir Abramovich Rokhlin', 'W. Hugh Woodin',
    # Section headers of the list itself, not problems.
    'Sudoku', 'Chess', 'Go (game)', 'Tic-tac-toe variants',
    # Broader topics of which the problem is one section. Tested by asking whether the article's
    # own bolded lead terms name the problem; every one below was then confirmed by reading it.
    'Analytic capacity',                # problem is Vitushkin's conjecture
    'Bombieri–Vinogradov theorem',      # problem is the density hypothesis
    'Greedy embedding',                 # problem is the strong Papadimitriou–Ratajczak conjecture
    'Powerful number',                  # problem is the Erdős–Mollin–Walsh conjecture
    'Quantum chaos',                    # problem is the Berry–Tabor conjecture
    'Restricted sumset',                # problem is the Erdős–Heilbronn conjecture
    'Sierpiński number',                # problem is Selfridge's conjecture
    'Special values of L-functions',    # problem is Beilinson's conjectures
    'Stable group',                     # problem is the Cherlin–Zilber conjecture
    "Van der Corput's method",          # problem is the exponent pair conjecture
    'Graceful labeling', 'graceful labeling',  # problems are Rosa's and the graceful tree conjecture
    'Petersen graph',                   # problem is Jaeger's Petersen-coloring conjecture
    'Unit distance graph',              # problem is the unit distance counting question
    'Graph factorization',              # problem is the perfect 1-factorization conjecture
    'Aliquot sequence',                 # problem is the Catalan–Dickson conjecture
    'Markov number',                    # problem is the uniqueness conjecture for Markov numbers
    'Graph toughness',                  # problem is Chvátal's toughness conjecture
    'uniform 5-polytope',               # problem is enumerating them
    'Lyapunov function',                # problem is about Lyapunov's second method
    'Euler equations (fluid dynamics)', # problem is finite-time blowup, one section of the article
    'Resolution of singularities',      # problem is the characteristic-p case
    # Judged NOT broader, though a heuristic flagged them: 'Quadrisecant' and 'Circle packing in an
    # equilateral triangle' are each the problem's own home article under a slightly different name.
}


PAGES = json.load(open(P('page_history.json'), encoding='utf-8'))['pages'] if os.path.exists(P('page_history.json')) else {}
for r in records:
    h = PAGES.get(r['primary_wikilink']) if r['primary_wikilink'] else None
    st = h['snapshot_state'] if h else ('unknown' if r['primary_wikilink'] else 'none')
    if st == 'redirect':
        st = 'alias' if r['primary_wikilink'] in PAGE_ALIAS else 'broader'
    if st == 'article' and r['primary_wikilink'] in PAGE_BROADER:
        st = 'broader'
    r['page_snapshot'] = st
    r['page_redirect_target'] = (h or {}).get('redirect_target')
    r['page_created'] = (h or {}).get('created')
    r['own_page_now'] = bool(r['primary_wikilink']) and r['primary_wikilink'] not in PAGE_BROADER
    r['own_page_2024'] = st in ('article', 'alias')
if PAGES:
    print('page at snapshot:', dict(Counter(r['page_snapshot'] for r in records)))
    unknown = [r['primary_wikilink'] for r in records if r['page_snapshot'] == 'unknown']
    if unknown: print(f'PAGE HISTORY INCOMPLETE: {len(unknown)} titles unfetched, run pipeline/stage_1_fetch_the_frozen_list/fetch_article_history.py')
    stale = PAGE_ALIAS - {r['primary_wikilink'] for r in records if r['page_snapshot'] == 'alias'}
    if stale: print('PAGE_ALIAS ENTRIES NOT MATCHED:', sorted(stale))
else:
    print('no page_history.json; own_page_2024 is false everywhere until pipeline/stage_1_fetch_the_frozen_list/fetch_article_history.py runs')
_hits = Counter(r['research_key'] for r in records if r['research_key'])
_dup = [(k, v) for k, v in _hits.items() if v > 1]
if _dup: print('ONE RESEARCH RECORD LANDED ON SEVERAL BULLETS:', _dup)

PROBLEMS = [r for r in records if not r['is_grouping']]
meta = dict(source='Wikipedia, "List of unsolved problems in mathematics"', revision=REV,
            n_unsolved=len(PROBLEMS), n_bullets=len(records), n_groupings=len(records) - len(PROBLEMS),
            n_solved=len(solved),
            fields=sorted({r['field'] for r in records}),
            notes=['year_introduced is not on the Wikipedia list. It was established by a pass of its own: read mechanically off the linked article where the infobox or lead states it (pipeline/stage_1_fetch_the_frozen_list/scrape_years.py, year_source "Wikipedia infobox" or "Wikipedia article lead"), otherwise researched one problem per agent run against the literature (pipeline/stage_5_date_each_problem/year_posed.py, year_source "mathematical literature (sourced)"), with a quote recorded in year_note. A problem whose year no source states carries none. The mechanical read has known false positives where a dating verb sits beside a year that is not the posing year — the Collatz article\'s "Lagarias stated in 2010" dated it to 2010 — so treat "Wikipedia article lead" years as the weakest of the three.',
                   'The problem list reflects the 26 Jan 2024 revision; status fields describe what has happened since.',
                   'The page has 467 bullets, ten of which are headings the article uses to group the problems beneath them (Sudoku, Chess, Go, Landau\'s problems, Kaplansky\'s conjectures and five others). They carry is_grouping=true, were never researched, and are excluded from every count: the denominator is 457 problems.',
                   'The six Millennium Prize Problems appear in the page introduction rather than the field lists and were added as records 463–467.',
                   'status / year_resolved / resolved_by / ai_involvement / status_sources were researched on 22-24 Sep 2026 for this version, with hand corrections through 28 Sep, from primary sources opened one by one (arXiv abstracts and full texts, authors\' own accounts, Tao and Oum digestions, lab announcements, Lean repositories). Several 2026 items are recent preprints, machine-checked certificates or press releases and have not completed peer review. Every problem on the list was researched individually by an agent (one problem per run), so absence of an entry means the research found no change, not that nobody looked.',
                   'Status codes: resolved = settled and accepted by experts or checkable by hand/computer algebra; claimed = preprint, announcement or machine-checked certificate not yet digested by experts; partial = a listed sub-question or major special case settled; progress = a bound moved or an instructive incident; open_stale = already settled before the 26 Jan 2024 snapshot (shown, but not counted as a change); open = still open (a status_note may record a pre-snapshot claim, also not counted).',
                   "ai_involvement: generated = an AI system produced the proof or counterexample and people checked it; assisted = human-led work in which, by the authors' own account, an AI system did a substantial part of the work (checking, proofreading or Lean formalisation alone does not qualify); incident = an AI-produced claim that was withdrawn; none.",
                   'month_resolved is the month of the preprint, announcement or posting, not of journal publication.',
                   'resolution_direction says which way a result went: refuted = the conjecture is false or the question was answered against expectation; confirmed = proved, or answered as expected; mixed = listed sub-cases went both ways; null = no direction, meaning a bound moved or nothing was settled. It is coded per problem by the deep-dive pass (DEEP_DIVE.md §6.4).'],
            version=VERSION, status_checked=STATUS_CHECKED)

model_releases = {m: dict(release=v.get('release'), preview_date=v.get('preview_date'),
                          available=v.get('available'),
                          release_confidence=v.get('release_basis') or 'unresearched',
                          inherited_from=v.get('inherited_from'), release_url=v.get('release_url'),
                          lab=v.get('lab'), family=v.get('family'), kind=v.get('kind'),
                          generated=sum(1 for r in records if m in r['ai_models'] and r['ai_involvement'] == 'generated'),
                          assisted=sum(1 for r in records if m in r['ai_models'] and r['ai_involvement'] == 'assisted'))
                  for m, v in sorted(MODELS.items())}

# Display names, applied after every join on the canonical ones. A source string is replaced only
# when it carries no version of its own: "OpenAI Codex (GPT-5.6 family)" keeps its detail.
from model_aliases import ALIASES
shown =lambda m: f'{m} (unknown version)' if m in UNVERSIONED else m
shown_raw = lambda s: shown(ALIASES[s.strip()]) if ALIASES.get(s.strip()) in UNVERSIONED and not re.search(r'\d', s) else s
for r in records:
    r['ai_models'] = [shown(m) for m in r['ai_models']]
    r['predates_models'] = [shown(m) for m in r['predates_models']]
    r['ai_system'] = '; '.join(dict.fromkeys(shown_raw(s) for s in r['ai_systems'])) or None
    for e in r.get('events') or []:                     # the same names on events, to match MODEL_RELEASES
        e['ai_models'] = [shown(m) for m in e['ai_models']]
model_releases = {shown(m): v for m, v in model_releases.items()}
LAB_OF_MODEL.update({shown(m): LAB_OF_MODEL[m] for m in UNVERSIONED if m in LAB_OF_MODEL})
meta['notes'].append('ai_model_releases.release is the public release date and preview_date the private preview where there was one; `available` is the earlier of the two and is what predates_availability compares a result against. release_confidence: sourced = a quoted source for that system; tier = a reasoning tier carrying its base model\'s dates; none_exists = an internal build, harness or product line with no release; unresearched = no source found; unversioned = a product or family name that pins down no model (shown as "(unknown version)"), so it carries no date; tentative = no public release, placed provisionally (the OpenAI internal model, on the day after GPT-6 Astra\'s release) and not a sourced date. Dates were researched one system per agent run (pipeline/stage_6_merge_and_date_the_models/release_dates.py); labs come from pipeline/shared/model_aliases.py.')
meta['notes'].append('predates_availability is true where a problem\'s result appeared before a model credited on it was available to anyone, comparing at the precision the result\'s date carries. predates_models names which ones.')

json.dump(dict(meta=meta, problems=records, solved_since_1995=solved, ai_model_releases=model_releases), open(P('unsolved_problems_db.json'), 'w'), indent=1, ensure_ascii=False)

with open(P('unsolved_problems.csv'), 'w', newline='') as f:
    cols = ['id', 'name', 'field', 'subfield', 'type', 'year_introduced', 'year_source', 'year_note', 'named_after', 'description', 'statement',
            'primary_wikilink', 'wikipedia_url', 'wikilinks', 'n_wikilinks', 'list_depth', 'parent', 'millennium_prize', 'hilbert_problem',
            'smale_problem', 'landau_problem', 'has_formula', 'source_revision', 'status', 'outcome', 'resolution_direction', 'year_resolved', 'resolved_by', 'ai_involvement', 'ai_system', 'status_note', 'status_sources', 'ai_models', 'ai_labs', 'month_resolved',
            'hand_corrected', 'judge_corrected', 'corrected_fields', 'page_snapshot', 'page_redirect_target', 'page_created', 'own_page_now', 'own_page_2024']
    w = csv.DictWriter(f, cols, extrasaction='ignore'); w.writeheader()
    for r in records:
        rr = dict(r); rr['named_after'] = '; '.join(r['named_after']); rr['wikilinks'] = '; '.join(r['wikilinks']); rr['status_sources'] = ' '.join(r['status_sources']); rr['ai_models'] = '; '.join(r['ai_models']); rr['ai_labs'] = '; '.join(r['ai_labs']); w.writerow(rr)
with open(P('solved_since_1995.csv'), 'w', newline='') as f:
    cols = ['name', 'field', 'decade_section', 'year_solved', 'solved_by', 'disproof', 'wikipedia_url', 'wikilinks', 'statement']
    w = csv.DictWriter(f, cols); w.writeheader()
    for s in solved:
        ss = dict(s); ss['wikilinks'] = '; '.join(s['wikilinks']); w.writerow(ss)

import os
if os.path.exists(P('unsolved_problems.sqlite')): os.remove(P('unsolved_problems.sqlite'))
con = sqlite3.connect(P('unsolved_problems.sqlite'))
con.executescript('''
CREATE TABLE problems(id INTEGER PRIMARY KEY, name TEXT, field TEXT, subfield TEXT, type TEXT, year_introduced INTEGER, year_source TEXT,
 year_note TEXT, description TEXT, statement TEXT, primary_wikilink TEXT, wikipedia_url TEXT, n_wikilinks INTEGER, list_depth INTEGER,
 parent TEXT, millennium_prize INTEGER, hilbert_problem INTEGER, smale_problem INTEGER, landau_problem INTEGER, has_formula INTEGER, source_revision INTEGER,
 status TEXT, outcome TEXT, resolution_direction TEXT, year_resolved INTEGER, resolved_by TEXT, ai_involvement TEXT, ai_system TEXT, status_note TEXT,
 month_resolved TEXT, hand_corrected INTEGER, judge_corrected INTEGER, corrected_fields TEXT,
 page_snapshot TEXT, page_redirect_target TEXT, page_created TEXT, own_page_now INTEGER, own_page_2024 INTEGER);
CREATE TABLE status_sources(problem_id INTEGER REFERENCES problems(id), url TEXT);
CREATE TABLE problem_corrections(problem_id INTEGER REFERENCES problems(id), date TEXT, corrected_by TEXT, field TEXT, from_value TEXT, to_value TEXT, why TEXT);
CREATE TABLE problem_ai_models(problem_id INTEGER REFERENCES problems(id), model TEXT, lab TEXT);
CREATE TABLE ai_model_releases(model TEXT PRIMARY KEY, lab TEXT, family TEXT, release_date TEXT, release_confidence TEXT, n_generated INTEGER, n_assisted INTEGER);
CREATE TABLE problem_links(problem_id INTEGER REFERENCES problems(id), position INTEGER, title TEXT, url TEXT);
CREATE TABLE problem_named_after(problem_id INTEGER REFERENCES problems(id), person TEXT);
CREATE TABLE solved_since_1995(id INTEGER PRIMARY KEY, name TEXT, field TEXT, decade_section TEXT, year_solved INTEGER, solved_by TEXT, disproof INTEGER, wikipedia_url TEXT, statement TEXT);
CREATE TABLE meta(key TEXT, value TEXT);
''')
for r in records:
    con.execute('INSERT INTO problems VALUES (' + ','.join('?' * 38) + ')',
                (r['id'], r['name'], r['field'], r['subfield'], r['type'], r['year_introduced'], r['year_source'], r['year_note'], r['description'],
                 r['statement'], r['primary_wikilink'], r['wikipedia_url'], r['n_wikilinks'], r['list_depth'], r['parent'], int(r['millennium_prize']),
                 r['hilbert_problem'], r['smale_problem'], int(r['landau_problem']), int(r['has_formula']), r['source_revision'],
                 r['status'], r['outcome'], r['resolution_direction'], r['year_resolved'], r['resolved_by'], r['ai_involvement'], r['ai_system'], r['status_note'],
                 r['month_resolved'], int(r['hand_corrected']), int(r['judge_corrected']), r['corrected_fields'],
                 r['page_snapshot'], r['page_redirect_target'], r['page_created'], int(r['own_page_now']), int(r['own_page_2024'])))
    for u in r['status_sources']:
        con.execute('INSERT INTO status_sources VALUES (?,?)', (r['id'], u))
    for c in r['corrections']:
        con.execute('INSERT INTO problem_corrections VALUES (?,?,?,?,?,?,?)',
                    (r['id'], c.get('date'), c.get('by'), c.get('field'),
                     *(v if v is None or isinstance(v, str) else json.dumps(v) for v in (c.get('from'), c.get('to'))), c.get('why')))
    for m in r['ai_models']:
        con.execute('INSERT INTO problem_ai_models VALUES (?,?,?)', (r['id'], m, LAB_OF_MODEL.get(m)))
    for i, t in enumerate(r['wikilinks']):
        con.execute('INSERT INTO problem_links VALUES (?,?,?,?)', (r['id'], i, t, 'https://en.wikipedia.org/wiki/' + t.replace(' ', '_')))
    for p in r['named_after']:
        con.execute('INSERT INTO problem_named_after VALUES (?,?)', (r['id'], p))
for i, s in enumerate(solved, 1):
    con.execute('INSERT INTO solved_since_1995 VALUES (?,?,?,?,?,?,?,?,?)', (i, s['name'], s['field'], s['decade_section'], s['year_solved'], s['solved_by'], int(s['disproof']), s['wikipedia_url'], s['statement']))
for m, v in model_releases.items():
    con.execute('INSERT INTO ai_model_releases VALUES (?,?,?,?,?,?,?)', (m, v['lab'], v['family'], v['release'], v['release_confidence'], v['generated'], v['assisted']))
for k, v in [('source_revision', REV['revid']), ('source_timestamp', REV['timestamp']), ('source_url', REV['url']), ('status_checked', STATUS_CHECKED), ('version', VERSION)]:
    con.execute('INSERT INTO meta VALUES (?,?)', (k, str(v)))
con.commit(); con.close()

from collections import Counter
print(len(records), 'problems;', len(solved), 'solved')
print('years known:', sum(1 for r in records if r['year_introduced'] is not None), Counter(r['year_source'] for r in records))
print(Counter(r['type'] for r in records))
print('named_after nonempty:', sum(1 for r in records if r['named_after']))
print(Counter(r['status'] for r in records)); print(Counter(r['ai_involvement'] for r in records))
print('direction:', dict(Counter(r['resolution_direction'] for r in records if r['resolution_direction'])),
      '| of the AI ones:', dict(Counter(r['resolution_direction'] for r in records if r['resolution_direction'] and r['ai_involvement'] not in ('none', 'incident'))))
mc = Counter(m for r in records for m in r['ai_models']); print('models:', dict(mc))
miss = [r['name'] for r in records if r['status'] in ('resolved','claimed','partial','progress') and not r['month_resolved']]
print('no month:', miss)

# ---- the site: embed the dataset and assemble the published page
# site/ holds both the sources (explorer_head.html, explorer_app.js, logo.b64) and what this
# writes (data.js, unsolved_problems_explorer.html).
SITE_DIR = os.path.join(ROOT, 'site')
OUT_SITE = os.path.abspath(_args.site_dir) if _args.site_dir else SITE_DIR
os.makedirs(OUT_SITE, exist_ok=True)
compact = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))
data_js = 'const ALL_DATA=' + compact(records) + ';\nconst SOLVED=' + compact(solved) + ';\nconst MODEL_RELEASES=' + compact(model_releases) + ';\n'
open(os.path.join(OUT_SITE, 'data.js'), 'w', encoding='utf-8').write(data_js)
head = open(os.path.join(SITE_DIR, 'explorer_head.html'), encoding='utf-8').read()
# The page is standalone — no server, no network — so the masthead logo is inlined as a data URI.
# site/logo.b64 is a web-sized copy of site/logos/MIT FutureTech logo.png, generated once;
# regenerate it if the logo changes.
head = head.replace('__LOGO__', open(os.path.join(SITE_DIR, 'logo.b64'), encoding='utf-8').read().strip())
# The About tab's review date is substituted from STATUS_CHECKED rather than written into the
# markup, so it cannot drift from the dataset it describes.
_d = datetime.date.fromisoformat(STATUS_CHECKED)
head = head.replace('__STATUS_CHECKED__', f'{_d.day} {_d.strftime("%B")} {_d.year}')
app = open(os.path.join(SITE_DIR, 'explorer_app.js'), encoding='utf-8').read()
explorer = head + '<script>\n' + data_js + app + '</script>\n'
standalone = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n' + explorer + '</html>\n'
open(os.path.join(OUT_SITE, 'unsolved_problems_explorer.html'), 'w', encoding='utf-8').write(standalone)
site_rel = os.path.relpath(OUT_SITE, ROOT)
print('wrote', DATA_DIR, f'{site_rel}/data.js, {site_rel}/unsolved_problems_explorer.html')

manifest.record(ROOT, VERSION, 'build', os.path.abspath(__file__),
                counts=dict(problems=len(records),
                            moved=sum(1 for r in records if r['status'] != 'open'),
                            with_ai=sum(1 for r in records if r['ai_involvement'] != 'none')),
                extra=dict(status_checked=STATUS_CHECKED,
                           wrote=['unsolved_problems_db.json', 'unsolved_problems.csv',
                                  'unsolved_problems.sqlite', f'{site_rel}/data.js',
                                  f'{site_rel}/unsolved_problems_explorer.html']), started=STARTED)
