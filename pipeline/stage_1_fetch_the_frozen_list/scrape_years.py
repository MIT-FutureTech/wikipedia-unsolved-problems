"""Read the year a problem was posed straight off its Wikipedia article, where the article says it.

Free, mechanical and exact: no agent, no judgement. For each problem it takes the article the
frozen bullet links, fetches that article's current wikitext in batches from the API, and looks in
the two places the encyclopedia states a date plainly:

  infobox   {{Infobox mathematical statement | conjectured in = 1939 }}
  lead      "conjectured by Ott-Heinrich Keller in 1939", "posed in 1955", "a 1966 problem of ..."

Nothing is guessed. A problem whose article states no year simply gets no entry, and is left for
pipeline/stage_5_date_each_problem/year_posed.py to research. Writes data/<VERSION>/year_scraped.json.

Run: python3 pipeline/stage_1_fetch_the_frozen_list/scrape_years.py   (network; ~10 API calls for ~300 titles)
"""
import argparse, json, os, re, subprocess, sys, time, urllib.parse

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest
from wikitext import first_link, parse_problem_keys, strip_wiki, MILLENNIUM_INTRO

_ap = argparse.ArgumentParser()
_ap.add_argument('--version', required=True, metavar='NAME',
                 help='the dataset version to work in: data/<NAME>/ — e.g. mark_2026-09-22')
VERSION = _ap.parse_args().version
STARTED = manifest.now()
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, 'data', VERSION)
API = 'https://en.wikipedia.org/w/api.php'
UA = 'wikipedia-open-problems-audit/1.0 (research; contact via repository)'

# Infobox date fields, in the order we trust them.
INFOBOX = [re.compile(r'\|\s*(?:conjecture|first\s+stated|proposed|posed)\s+date\s*=\s*\[?\[?(\d{3,4})', re.I),
           re.compile(r'\|\s*conjectured\s+in\s*=\s*\[?\[?(\d{3,4})', re.I),
           re.compile(r'\|\s*first\s+(?:stated|posed|proposed|published)\s*(?:in)?\s*=\s*\[?\[?(\d{3,4})', re.I)]
# A bare `| date = ` field is NOT in this list: on these articles it is usually a maintenance tag
# ({{citation needed|date=2026}}, {{update|date=...}}), and it dated Crouzeix's conjecture — posed
# in 2004 — to 2026 before it was removed.

# Dating phrases in the lead. Each must tie a year to the act of posing the problem — a bare year
# anywhere in the prose is not evidence, and is deliberately not matched.
LEAD = [re.compile(r'(?:conjectured|posed|proposed|formulated|asked|raised|stated|introduced)\s+'
                   r'(?:by\s+[^.]{1,60}?\s+)?in\s+(\d{4})', re.I),
        re.compile(r'\ba\s+(\d{4})\s+(?:conjecture|problem|question)\s+(?:of|by|due to)\b', re.I),
        re.compile(r'(?:conjecture|problem|question)[^.]{0,40}?\bfirst\s+(?:stated|posed|proposed|'
                   r'formulated|asked|appeared)[^.]{0,30}?\bin\s+(\d{4})', re.I),
        re.compile(r'\bdates?\s+back\s+to\s+(\d{4})', re.I),
        re.compile(r'\bin\s+(\d{4}),\s+[A-Z][^.]{0,60}?\s+(?:conjectured|posed|asked|proposed)\b')]


def api(params, tries=4):
    """One API call, retried: the API throttles a burst of 40-title requests with an empty body."""
    params = dict(params, format='json', formatversion='2')
    url = API + '?' + urllib.parse.urlencode(params)
    for attempt in range(tries):
        r = subprocess.run(['curl', '-s', '-m', '60', '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            time.sleep(3 * (attempt + 1))
    sys.exit('the API kept returning a non-JSON body; try again in a minute')


def titles_by_key(revision):
    """key -> the article the bullet links, joined on statement text (as build.py joins)."""
    src = open(os.path.join(DATA, 'page.wiki'), encoding='utf-8').read()
    src = src[:src.index('== See also ==')]
    by_statement, mode = {}, None
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
        if fl:
            by_statement[strip_wiki(bm.group(2))] = fl[0]
    out, mill = {}, dict(zip(
        ['birch-and-swinnerton-dyer-conjecture', 'hodge-conjecture',
         'navier-stokes-existence-and-smoothness', 'p-versus-np-problem',
         'yang-mills-existence-and-mass-gap'], MILLENNIUM_INTRO))
    for r in parse_problem_keys(os.path.join(ROOT, 'data', VERSION, 'problem_keys.md'), revision):
        if r['is_grouping']:
            continue
        t = by_statement.get(r['statement']) or mill.get(r['key'])
        if t:
            out[r['key']] = t
    return out


def year_from(text):
    """(year, basis, quote) from an article's wikitext, or None. The infobox wins."""
    for rx in INFOBOX:
        m = rx.search(text)
        if m and 1000 < int(m.group(1)) <= 2026:
            return int(m.group(1)), 'wikipedia_infobox', m.group(0).strip()
    lead = strip_wiki(re.sub(r'\{\{[^{}]*\}\}', ' ', text[:6000]))
    for rx in LEAD:
        m = rx.search(lead)
        if m and 1000 < int(m.group(1)) <= 2026:
            s = max(0, m.start() - 60)
            return int(m.group(1)), 'wikipedia_lead', lead[s:m.end() + 40].strip()
    return None


KEYS = titles_by_key('2024-01')
titles = sorted(set(KEYS.values()))
print(f'{len(KEYS)} problems link {len(titles)} distinct articles')

wikitext = {}
for i in range(0, len(titles), 40):
    chunk = titles[i:i + 40]
    j = api(dict(action='query', prop='revisions', rvprop='content', rvslots='main',
                 titles='|'.join(chunk), redirects=1))
    norm = {r['from']: r['to'] for r in j.get('query', {}).get('normalized', [])}
    red = {r['from']: r['to'] for r in j.get('query', {}).get('redirects', [])}
    got = {}
    for p in j.get('query', {}).get('pages', []):
        if p.get('missing') or 'revisions' not in p:
            continue
        got[p['title']] = p['revisions'][0]['slots']['main']['content']
    for t in chunk:
        resolved = red.get(norm.get(t, t), norm.get(t, t))
        if resolved in got:
            wikitext[t] = got[resolved]
    print(f'  fetched {min(i + 40, len(titles))}/{len(titles)}', flush=True)
    time.sleep(1)

out, miss = {}, []
for key, title in sorted(KEYS.items()):
    text = wikitext.get(title)
    if not text:
        miss.append(key)
        continue
    hit = year_from(text)
    if not hit:
        miss.append(key)
        continue
    year, basis, quote = hit
    out[key] = dict(key=key, year=year, approx=False, basis=basis, quote=quote,
                    url='https://en.wikipedia.org/wiki/' + title.replace(' ', '_'),
                    posed_by=None, note='', source='scrape')

os.makedirs(DATA, exist_ok=True)
json.dump(out, open(os.path.join(DATA, 'year_scraped.json'), 'w', encoding='utf-8'),
          indent=1, ensure_ascii=False)
import collections
print(f'\n{len(out)} of {len(KEYS)} problems dated from their article '
      f'({100 * len(out) / len(KEYS):.0f}%)')
print('  basis:', dict(collections.Counter(v['basis'] for v in out.values())))
print(f'  {len(miss)} left for the agent pass')
print('-> ' + os.path.relpath(os.path.join(DATA, 'year_scraped.json'), ROOT))

manifest.record(ROOT, VERSION, 'fetch', os.path.abspath(__file__),
                counts=dict(problems=len(KEYS), dated=len(out), undated=len(miss),
                            basis=dict(collections.Counter(v['basis'] for v in out.values()))),
                extra=dict(wrote='year_scraped.json'), started=STARTED)
