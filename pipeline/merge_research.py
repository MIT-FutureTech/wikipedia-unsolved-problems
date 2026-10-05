"""Turn the deep-dive records into the tables build.py joins onto the frozen list.

One record per problem comes out of pipeline/deep_dive.py, keyed by slug. build.py works from the
wikitext and knows nothing about slugs, so this is where the two meet:

  * the join is on statement text (pipeline/join_map.py explains why, and carries the exceptions)
  * system names are canonicalised through pipeline/model_aliases.py
  * `year_introduced` is not researched yet — year_introduced() below is the stub

Writes data/<VERSION>/research.json:

  by_statement  statement text -> the finding, for the 457 bullets
  by_name       build record name -> the finding, for the 5 Millennium problems
  models        canonical model -> lab, family, kind, release
  meta          trial, counts, and every problem the merge could not place

Run: python3 pipeline/merge_research.py [--trial mark_2026-09-22]
"""
import argparse, collections, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from join_map import BY_NAME
from model_aliases import MODELS, ALIASES
from wikitext import parse_problem_keys, strip_wiki

VERSION = 'sonnet-2026-09-22'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument('--trial', default='mark_2026-09-22')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--live', action='store_true', help='ignore the judging pass and use only the research records')
args = ap.parse_args()

OUT_DIR = os.path.join(ROOT, 'data', VERSION)
RECORDS = os.path.join(ROOT, 'deepdive', args.trial, 'out')
# The judging pass (pipeline/judge.py) writes corrected copies here. Where one exists it replaces the
# research record, unless a human has since overruled the judge on that record, which the live
# record says in a correction whose `by` contains OVERRULES.
JUDGED = os.path.join(ROOT, 'deepdive', args.trial, 'judged', 'out')


def load_record(f):
    live = json.load(open(os.path.join(RECORDS, f), encoding='utf-8'))
    path = os.path.join(JUDGED, f)
    if args.live or not os.path.exists(path):
        return live, 'research'
    if any('OVERRULES' in (c.get('by') or '') for c in live.get('corrections') or []):
        return live, 'overruled'
    judged = json.load(open(path, encoding='utf-8'))
    if judged.get('judge_problems', ['not validated']):
        return live, 'judged-invalid'
    return judged, 'judged'


def statements(revision):
    """slug -> statement, for every bullet including the article's own headings."""
    return {r['key']: r['statement']
            for r in parse_problem_keys(os.path.join(ROOT, 'problem_keys.md'), revision)}


def groupings(revision):
    """slug -> statement for the bullets that are headings, not problems.

    Two sources, and they turn out to be disjoint: problem_keys.md marks a bullet [GROUPING] when
    it ends in a colon and has children, and the triage pass marked five more `skip` by judgement
    (Kaplansky's conjectures, the Deligne conjecture, Landau's problems and two 'Problems in …'
    headings). Neither alone is complete, so build.py excludes the union.
    """
    rows = parse_problem_keys(os.path.join(ROOT, 'problem_keys.md'), revision)
    out = {r['key']: r['statement'] for r in rows if r['is_grouping']}
    tri = os.path.join(ROOT, 'triage', revision, 'out')
    if os.path.isdir(tri):
        for f in sorted(os.listdir(tri)):
            if f.endswith('.json') and json.load(open(os.path.join(tri, f), encoding='utf-8')).get('verdict') == 'skip':
                key = f[:-5]
                if key in STATEMENTS_ALL:
                    out[key] = STATEMENTS_ALL[key]
    return out


def release_dates():
    """canonical model -> the release pass's finding, or {} if that pass has not run.

    `available` is the date that matters for comparing against a result: the private preview where
    there was one, otherwise the public release. A system its users could reach in May 2025 was
    available in May 2025, whatever month it later reached general availability.

    A tier with no date of its own inherits its base model's dates and is marked inherited, so a
    reader can tell a sourced date from a carried one.
    """
    path = os.path.join(OUT_DIR, 'release_dates.json')
    if not os.path.exists(path):
        return {}
    raw = json.load(open(path, encoding='utf-8'))
    out = {}
    for m, r in raw.items():
        out[m] = dict(release=r.get('release'), preview_date=r.get('preview_date'),
                      release_basis=r.get('release_basis'), base_model=r.get('base_model'),
                      release_url=r.get('url'))
    for m, r in out.items():                       # tiers inherit, after everything is loaded
        if r['release_basis'] == 'tier' and r.get('base_model') in out and not r['release']:
            base = out[r['base_model']]
            r['release'], r['preview_date'] = base['release'], base['preview_date']
            r['inherited_from'] = r['base_model']
    for r in out.values():
        r['available'] = r.get('preview_date') or r.get('release')
    return out


def years_posed():
    """key -> the year-posed finding, or {} if neither pass has run.

    Two sources in one file, written by pipeline/year_posed.py: `scrape` where the year was read
    mechanically off the article (pipeline/scrape_years.py), `agent` where it was researched. The
    distinction is kept on every record — a regex over an article lead and a sourced literature
    citation are not the same kind of fact, and the scrape is known to have false positives where
    a dating verb sits next to a year that is not the posing year.
    """
    path = os.path.join(OUT_DIR, 'year_posed.json')
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}


YEAR_SOURCE = {'wikipedia_infobox': 'Wikipedia infobox',
               'wikipedia_lead': 'Wikipedia article lead',
               'literature': 'mathematical literature (sourced)',
               'unknown': None}


def year_introduced(key, statement):
    """(year, source, note, approx) for one problem; year is None where no source states one."""
    r = YEARS.get(key)
    if not r or r.get('year') is None:
        return (None, None, '', False)
    note = (r.get('quote') or '').strip()
    if r.get('posed_by'):
        note = f"{r['posed_by']}, {r['year']}" + (f" — {note}" if note else '')
    return (r['year'], YEAR_SOURCE.get(r.get('basis')) or r.get('basis'), note, bool(r.get('approx')))


def systems_of(record):
    """The record's system strings -> canonical models, plus anything the alias map has not seen.

    A record coded `ai_role: none` may still name systems — a model that only checked the proof,
    wrote the manuscript, or was tried and failed. Those names stay in `ai_systems` as evidence,
    but the record credits no model, so it contributes nothing to `ai_models` and nothing to the
    model table. Counting them would put GitHub Copilot on a problem whose authors say it
    formatted their LaTeX.
    """
    named = (record.get('ai') or {}).get('systems') or []
    if (record.get('ai_role') or 'none') == 'none':
        return named, [], []
    models, unknown = [], []
    for s in named:
        s = s.strip()
        if s not in ALIASES:
            unknown.append(s)
        elif ALIASES[s] and ALIASES[s] not in models:
            models.append(ALIASES[s])
    return named, models, unknown


def month_of(event):
    """'YYYY-MM', or 'YYYY-MM~' where only the year is sourced. Never invents a month."""
    date, prec = str(event.get('date') or ''), event.get('precision')
    if not re.match(r'\d{4}', date):
        return None
    if prec == 'year' or len(date) < 7:
        return None                      # a year with no month is a gap; build shows year only
    return date[:7]


def finding(r):
    """The record in the shape build.py expects, plus the fields the site shows."""
    ev = r.get('event') or {}
    ce = r.get('counterexample') or {}
    named, models, _ = systems_of(r)
    by = r.get('credited_humans') or []
    return dict(
        status=r['status'],
        outcome=r.get('outcome'),
        year=int(str(ev.get('date'))[:4]) if re.match(r'\d{4}', str(ev.get('date') or '')) else None,
        month=month_of(ev),
        by='; '.join(by) if isinstance(by, list) else (by or None),
        ai=r.get('ai_role') or 'none',
        ai_systems=named,                       # verbatim, as the sources named them
        ai_models=models,                       # canonical, for counting
        ai_labs=sorted({MODELS[m]['lab'] for m in models if MODELS[m]['lab']}),
        ai_quote=(r.get('ai') or {}).get('basis_quote'),
        direction=r.get('resolution_direction'),
        counterexample=bool(ce.get('is_counterexample')),
        note=r.get('summary') or '',
        competing_reading=r.get('competing_reading'),
        confidence=r.get('confidence'),
        sources=r.get('status_sources') or [],
        no_change_found=bool(r.get('no_change_found')),
        corrections=r.get('corrections') or [],
        key=r['key'],
    )


RELEASES = release_dates()
YEARS = years_posed()
STATEMENTS_ALL = statements(args.revision)
stmt = STATEMENTS_ALL
GROUPINGS = groupings(args.revision)
if not os.path.isdir(RECORDS):
    sys.exit(f'no records in {os.path.relpath(RECORDS, ROOT)} — run pipeline/deep_dive.py first')

by_statement, by_name, unplaced, unknown_systems = {}, {}, [], collections.Counter()
n, source = 0, collections.Counter()
for f in sorted(os.listdir(RECORDS)):
    if not f.endswith('.json'):
        continue
    r, src = load_record(f)
    source[src] += 1
    key = r.get('key') or f[:-5]
    n += 1
    _, _, unk = systems_of(r)
    for u in unk:
        unknown_systems[u] += 1
    fnd = finding(r)
    fnd['year_introduced'] = year_introduced(key, stmt.get(key))
    if key in BY_NAME:
        by_name[BY_NAME[key]] = fnd
    elif key in stmt:
        by_statement[stmt[key]] = fnd
    else:
        unplaced.append(key)

moved = {k: v for d in (by_statement, by_name) for k, v in d.items() if v['status'] != 'open'}
out = dict(
    by_statement=by_statement, by_name=by_name,
    groupings=sorted(GROUPINGS.values()),
    models={m: dict(MODELS[m], **RELEASES.get(m, {}))
            for m in sorted({m for v in list(by_statement.values()) + list(by_name.values()) for m in v['ai_models']})},
    meta=dict(trial=args.trial, revision=args.revision, n_records=n,
              n_placed=len(by_statement) + len(by_name), n_moved=len(moved),
              unplaced=unplaced, unknown_systems=dict(unknown_systems),
              n_groupings=len(GROUPINGS),
              year_introduced='stub: not researched in this version'),
)
os.makedirs(OUT_DIR, exist_ok=True)
json.dump(out, open(os.path.join(OUT_DIR, 'research.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

print('records from: ' + '  '.join(f'{k}={v}' for k, v in source.most_common()))
print(f'{n} records -> {len(by_statement)} by statement + {len(by_name)} by name = {len(by_statement)+len(by_name)} placed')
print('status: ' + '  '.join(f'{k}={v}' for k, v in collections.Counter(
    v['status'] for v in list(by_statement.values()) + list(by_name.values())).most_common()))
print('ai:     ' + '  '.join(f'{k}={v}' for k, v in collections.Counter(
    v['ai'] for v in list(by_statement.values()) + list(by_name.values())).most_common()))
with_year = sum(1 for v in list(by_statement.values()) + list(by_name.values()) if v['year_introduced'][0])
print(f'year posed: {with_year} of {len(by_statement) + len(by_name)} problems')
dated = sum(1 for v in out['models'].values() if v.get('available'))
print(f'models named: {len(out["models"])} ({dated} with an availability date) | '
      f'grouping bullets excluded: {len(GROUPINGS)}')
if unplaced:
    print(f'UNPLACED ({len(unplaced)}) — no statement match and no join_map entry:')
    for k in unplaced:
        print('  ' + k)
if unknown_systems:
    print(f'SYSTEM STRINGS NOT IN model_aliases.py ({len(unknown_systems)}):')
    for s, c in unknown_systems.most_common():
        print(f'  {c:2}  {s}')
print('-> ' + os.path.relpath(os.path.join(OUT_DIR, 'research.json'), ROOT))
