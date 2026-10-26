"""Wikitext cleaning and bullet parsing shared across the pipeline.

Kept in one place so that every stage derives the same strings from the same bullet. That matters
most for first_link(): the title it returns is a problem's `primary_wikilink` in build.py and the
key fetch_article_history.py asks the API about, so the two must agree exactly or the article
history joins onto nothing.
"""
import html, re

LINK_RE = re.compile(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]')
MATH_RE = re.compile(r'<math>(.*?)</math>', re.S)


def links_of(s):
    out = []
    for m in LINK_RE.finditer(s):
        t = m.group(1).strip()
        if t.lower().startswith(('file:', 'category:')) or t in out:
            continue
        out.append(t)
    return out


def strip_wiki(s):
    s = re.sub(r'\{\{efn\|.*?\}\}', '', s)
    s = re.sub(r'\{\{Rp\|[^}]*\}\}', '', s)
    s = re.sub(r'\{\{not a typo\|(.*?)\}\}', r'\1', s)
    s = re.sub(r'\{\{nowrap\|1=(.*?)\}\}', r'\1', s)
    s = re.sub(r'\{\{nowrap\|(.*?)\}\}', r'\1', s)
    s = re.sub(r'\{\{mvar\|(.*?)\}\}', r'\1', s)
    # entity-escape '<' '>' inside <math> so the tag stripper below cannot eat the formula
    s = MATH_RE.sub(lambda m: '$' + m.group(1).strip().replace('<', '&lt;').replace('>', '&gt;') + '$', s)
    s = re.sub(r'\[\[(?:[^\]|]+)\|([^\]]*)\]\]', r'\1', s)
    s = re.sub(r'\[\[([^\]]+)\]\]', r'\1', s)
    s = re.sub(r"'''?", '', s)
    s = re.sub(r'<sup>(.*?)</sup>', r'^\1', s)
    s = re.sub(r'<sub>(.*?)</sub>', r'_\1', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', s).strip()


FIRST_LINK_RE = re.compile(
    r"^(?:[Tt]he\s+|Existence of\s+|Frankl's\s+|Convex\s+|Regularity of solutions of\s+"
    r"|Convergence of\s+|Solving the\s+|Many problems concerning an\s+)?"
    r"\{?\{?(?:not a typo\|)?(\[\[[^\]]+\]\])\}?\}?(s?)(.*)$", re.S)


def first_link(body):
    """If the bullet starts with (The) [[link]], return (title, display, rest_of_body)."""
    m = FIRST_LINK_RE.match(body)
    if not m:
        return None
    lm = LINK_RE.match(m.group(1))
    title = lm.group(1).strip()
    disp = (lm.group(2) if lm.group(2) is not None else lm.group(1)).strip()
    return title, strip_wiki(disp) + m.group(2), m.group(3)


# The five Millennium Prize Problems that the page names in its introduction rather than in a
# field list. build.py adds them as records of their own, so their articles need fetching too.
MILLENNIUM_INTRO = ['Birch and Swinnerton-Dyer conjecture', 'Hodge conjecture',
                    'Navier–Stokes existence and smoothness', 'P versus NP problem',
                    'Yang–Mills existence and mass gap']


def primary_titles(page_wiki):
    """Every problem bullet's opening wikilink, in page order, deduplicated.

    This is the set of articles the list treats as the problems' own pages, and the only reason
    it lives here is so that build.py and fetch_article_history.py cannot disagree about it.
    """
    src = page_wiki[:page_wiki.index('== See also ==')] if '== See also ==' in page_wiki else page_wiki
    out, mode = [], None
    for raw in src.split('\n'):
        line = raw.rstrip()
        hm = re.match(r'^(=+)\s*(.*?)\s*=+$', line)
        if hm:
            if len(hm.group(1)) == 2:
                mode = 'unsolved' if hm.group(2) == 'Unsolved problems' else None
            continue
        bm = re.match(r'^(\*+)\s*(.*)$', line)
        if not bm or mode != 'unsolved' or not bm.group(2).strip():
            continue
        fl = first_link(bm.group(2))
        if fl and fl[0] not in out:
            out.append(fl[0])
    return out + [t for t in MILLENNIUM_INTRO if t not in out]


# ---- problem_keys.md ------------------------------------------------------------------------
# The index make_problem_keys.py writes, read back by the research passes and by the merge. Kept
# here because all three parsed it with their own copy of the same regex, and the copies drifted:
# the [GROUPING ...] marker contains an em-dash of its own, so a naive split on ' — ' captured the
# tail of the marker as the problem's statement.

# Heading bullets the [GROUPING] marker cannot catch: they do not end in a colon, so
# make_problem_keys.py does not mark them, but the article uses them as headings for the bullets
# beneath. The triage pass established these five by judgement; that pass was removed on
# 7 Oct 2026, so its verdicts live here, where every pass filters on them — which is what keeps the
# denominator at 457 of the revision's 467 bullets.
HEADING_BULLETS = frozenset((
    'deligne-conjecture', 'kaplanskys-conjectures', 'landaus-problems',
    'problems-in-latin-squares', 'problems-in-loop-theory-and-quasigroup-theory'))

KEYS_BULLET = re.compile(r'^- `([^`]+)`(.*?) — (.+)$')
KEYS_GROUPING = re.compile(r'\*\*\[GROUPING[^\]]*\]\*\*')
KEYS_SUB_OF = re.compile(r'sub of `([^`]+)`')


def parse_problem_keys(path, revision):
    """[{key, field, subfield, statement, parent, parent_statement, is_grouping}] for one revision.

    Every bullet in the section, groupings included and flagged; callers filter. Order is the
    article's own. `is_grouping` covers both kinds of heading: the marked ones and HEADING_BULLETS.
    """
    out, field, sub, inside = [], None, None, False
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        if line.startswith('## Revision '):
            inside = line.startswith(f'## Revision {revision}')
        elif not inside:
            continue
        elif line.startswith('### '):
            head = line[4:].split(' — ', 1)
            field, sub = head[0].strip(), (head[1].strip() if len(head) > 1 else None)
        elif m := KEYS_BULLET.match(KEYS_GROUPING.sub('[GROUPING]', line)):
            tags = m.group(2)
            p = KEYS_SUB_OF.search(tags)
            out.append(dict(key=m.group(1), field=field, subfield=sub,
                            statement=m.group(3).strip(),
                            parent=p.group(1) if p else None,
                            is_grouping='GROUPING' in tags or m.group(1) in HEADING_BULLETS))
    stmt = {r['key']: r['statement'] for r in out}
    for r in out:                                  # resolved after the fact: a parent may be a grouping
        r['parent_statement'] = stmt.get(r['parent'])
    return out
