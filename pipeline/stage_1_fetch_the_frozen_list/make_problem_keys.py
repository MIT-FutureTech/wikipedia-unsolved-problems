"""Write problem_keys.md: the problem list for each January revision, keyed by readable slug.

One section per revision, each self-contained, so that whoever runs the research can delete the
sections they do not want and hand the rest to an agent unchanged.

Keys are slugs derived from the problem's name — `jacobian-conjecture`, `moving-sofa-problem` — so
that a record can be matched to a problem by eye. Where two problems on one revision produce the
same slug (the list carries two distinct "Hadwiger conjecture" bullets), the field is appended to
break the tie, and a numeric suffix after that.

Run: python3 pipeline/stage_1_fetch_the_frozen_list/make_problem_keys.py [2024-01] [2025-01] [2026-01]
     with no arguments it writes all three sections; name one or more to write only those.
"""
import argparse, os, re, subprocess, sys, unicodedata

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest
from wikitext import strip_wiki

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UA = 'wikipedia-open-problems-audit/1.0 (research; contact via repository)'
RAW = 'https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=%d&action=raw'

REVISIONS = [
    ('2024-01', 1199136318, '26 January 2024'),
    ('2025-01', 1272061095, '27 January 2025'),
    ('2026-01', 1335631179, '30 January 2026'),
]

REF_PAIR = re.compile(r'<ref\b[^>]*?(?<!/)>.*?</ref\s*>', re.S | re.I)
REF_SELF = re.compile(r'<ref\b[^>]*/\s*>', re.S | re.I)


def fetch(oldid):
    r = subprocess.run(['curl', '-s', '-m', '120', '-H', f'User-Agent: {UA}', RAW % oldid],
                       capture_output=True, text=True)
    t = r.stdout
    prev = None
    while prev != t:
        prev = t
        t = REF_PAIR.sub('', t)
    return REF_SELF.sub('', t)


LINK_OPEN = re.compile(r"^(?:[Tt]he\s+|Existence of\s+|Convergence of\s+|Solving the\s+|Improving\s+)?"
                       r"\{?\{?(?:not a typo\|)?\[\[([^\]|]+)(?:\|([^\]]*))?\]\]")
NAMEY = re.compile(r"^(.{3,72}?(?:conjectures?|problems?|hypothesis|question|theorem|notebook))\b", re.I)


def slug(s, maxlen=58):
    """Readable, ASCII, hyphenated key."""
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = s.replace('\u0141', 'L').replace('\u0142', 'l').replace('\u00f8', 'o').replace('\u0110', 'D').replace('\u0111', 'd')
    s = re.sub(r"[''\u2019]s\b", 's', s)
    s = re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()
    if len(s) > maxlen:
        s = s[:maxlen].rsplit('-', 1)[0]
    return s or 'problem'


def name_of(wikitext, clean):
    """A short human name for the bullet, for slugging."""
    m = LINK_OPEN.match(wikitext.strip())
    if m:
        disp = (m.group(2) or m.group(1)).strip()
        disp = strip_wiki(disp)
        rest = strip_wiki(wikitext.strip()[m.end():])
        # "[[Banach]]'s problem", "[[Birkhoff]] conjecture" — pull the noun in
        m2 = re.match(r"^((?:'s)?\s*(?:conjectures?|problem|hypothesis)\b)", rest)
        if m2 and len(disp.split()) <= 3:
            g = m2.group(1).strip()
            disp = disp + g if g.startswith("'") else disp + ' ' + g
        if 3 <= len(disp) <= 80:
            return disp
    t = re.sub(r'^[Tt]he\s+', '', clean)
    m = NAMEY.match(t)
    if m:
        return m.group(1)
    for sep in (': ', ' - ', ' \u2013 ', ' \u2014 '):
        if sep in t[:80]:
            head = t.split(sep, 1)[0]
            if 3 <= len(head) <= 80:
                return head
    return ' '.join(t.split()[:9])


def parse(text):
    """[(depth, field, subfield, statement, wikitext)] for the Unsolved problems section."""
    out, h3, h4, mode = [], None, None, None
    for raw in text.split('\n'):
        line = raw.rstrip()
        hm = re.match(r'^(=+)\s*(.*?)\s*=+$', line)
        if hm:
            lvl, title = len(hm.group(1)), hm.group(2)
            if lvl == 2:
                h3 = h4 = None
                mode = 'unsolved' if title == 'Unsolved problems' else None
            elif lvl == 3:
                h3, h4 = title, None
            elif lvl == 4:
                h4 = title
            continue
        bm = re.match(r'^(\*+)\s*(.*)$', line)
        if not bm or mode != 'unsolved' or not bm.group(2).strip():
            continue
        out.append((len(bm.group(1)), h3, h4, strip_wiki(bm.group(2)), bm.group(2)))
    return out


def intro_millennium(text):
    """The Millennium Prize Problems named in the page introduction."""
    head = text[:text.index('== Unsolved problems ==')] if '== Unsolved problems ==' in text else text[:8000]
    # The Riemann hypothesis is deliberately absent: it is a Millennium problem but it also
    # appears as a bullet in the number-theory list, and listing it here would create two keys
    # for one problem.
    names = ['Birch and Swinnerton-Dyer conjecture', 'Hodge conjecture',
             'Navier–Stokes existence and smoothness', 'P versus NP problem',
             'Yang–Mills existence and mass gap']
    return [n for n in names if n.split()[0] in head or n in head]


FIELD_TAG = {
    'Number theory': 'number-theory', 'Geometry': 'geometry', 'Graph theory': 'graph-theory',
    'Algebra': 'algebra', 'Analysis': 'analysis', 'Combinatorics': 'combinatorics',
    'Topology': 'topology', 'Set theory': 'set-theory', 'Dynamical systems': 'dynamical-systems',
    'Games and puzzles': 'games', 'Probability theory': 'probability',
    'Model theory and formal languages': 'model-theory',
}

lines = ['# Problem keys',
         '',
         "Problem lists taken from three January revisions of Wikipedia's *List of unsolved problems in",
         'mathematics*. Each section stands alone.',
         '',
         '**Delete the sections you do not want, then hand the rest to the research agent.** Keys are',
         'unique within a section only, so keep exactly one section unless you intend to research more',
         'than one revision.',
         '',
         'Each problem has a slug key, then its statement as the article words it. The `###` headings',
         'are the field and subfield, taken from the article\'s own section headings. A key marked',
         '`sub of <key>` is a nested bullet and cannot be read without its parent. A key marked',
         '**[GROUPING]** is a heading the article uses to group the bullets under it — it is not a',
         'problem and should not be researched.',
         '']

_ap = argparse.ArgumentParser()
_ap.add_argument('--version', required=True, metavar='NAME',
                 help='the dataset version to write into: data/<NAME>/problem_keys.md')
_ap.add_argument('revisions', nargs='*', metavar='CODE',
                 help='which January revisions to write; all of them when none is named')
_args = _ap.parse_args()
STARTED = manifest.now()
only = _args.revisions
for code, oldid, when in REVISIONS:
    if only and code not in only:
        continue
    text = fetch(oldid)
    rows = parse(text)
    mill = intro_millennium(text)

    # slug every bullet first, then break ties: field tag, then a numeric suffix
    raw = [slug(name_of(wt, st)) for _, _, _, st, wt in rows] + [slug(m) for m in mill]
    seen = {}
    for r in raw:
        seen[r] = seen.get(r, 0) + 1
    keys, used = [], {}
    fields = [f for _, f, _, _, _ in rows] + ['Millennium'] * len(mill)
    for r, f in zip(raw, fields):
        k = r
        if seen[r] > 1:
            tag = FIELD_TAG.get(f)
            k = f'{r}-{tag}' if tag else r
        while k in used:
            used[k] += 1
            k = f'{k}-{used[k]}'
        used.setdefault(k, 1)
        keys.append(k)

    lines += ['', '<!-- ================= DELETE FROM HERE TO THE NEXT BANNER TO DROP ' + code + ' ================= -->',
              '', f'## Revision {code} — {when}', '',
              f'- Revision id (oldid): **{oldid}**',
              f'- The revision as a normal page: <https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid={oldid}>',
              f'- The same revision as raw wikitext: <https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid={oldid}&action=raw>',
              f'- Problems in this section: **{len(rows) + len(mill)}** ({len(rows)} list bullets, {len(mill)} from the introduction)',
              '',
              'This section is an index, not a copy of the page. It lists only the problems, with their',
              'wikitext markup resolved to plain text. The article also has an introduction, a',
              '"Problems solved" section and reference lists, none of which appear here. Open one of the',
              'links above to see the revision itself.',
              '']
    field = sub = None
    parents = {}
    for i, (depth, f, s_, stmt, _wt) in enumerate(rows):
        parents[depth] = keys[i]
        if f != field or s_ != sub:
            field, sub = f, s_
            lines += ['', f'### {field}' + (f' — {sub}' if sub else ''), '']
        tag = f' *(sub of `{parents.get(depth - 1, "?")}`)*' if depth > 1 else ''
        # A bullet that ends in a colon and has children is a heading, not a problem: the article
        # uses it to group the bullets underneath. Flag it so it is not researched as a problem.
        is_container = stmt.rstrip().endswith(':') and i + 1 < len(rows) and rows[i + 1][0] > depth
        if is_container:
            tag += ' **[GROUPING — not a problem; do not research. Its sub-problems follow.]**'
        lines.append(f'- `{keys[i]}`{tag} — {stmt}')
    if mill:
        lines += ['', '### Millennium Prize Problems — named in the article introduction, not in a field list',
                  '',
                  '(The Riemann hypothesis is the sixth Millennium problem on this page. It already has a',
                  'key above, as a bullet in the number-theory list, and is not repeated here.)', '']
        for j, m in enumerate(mill):
            lines.append(f'- `{keys[len(rows) + j]}` — {m}')
    lines += ['', '<!-- ================= END OF ' + code + ' ================= -->', '']

# The index belongs to the trial, not the repo: a later trial rewriting a shared file would
# silently re-key the records of an earlier one.
OUT = os.path.join(ROOT, 'data', _args.version, 'problem_keys.md')
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
print('wrote ' + os.path.relpath(OUT, ROOT))

manifest.record(ROOT, _args.version, 'fetch', os.path.abspath(__file__),
                counts=dict(revisions=[c for c, _, _ in REVISIONS if not only or c in only],
                            lines=len(lines)),
                extra=dict(wrote=os.path.relpath(OUT, ROOT)), started=STARTED)
