"""Per-article history for every title the list links as a problem's own page.

For each title we ask what stood at that title on the snapshot date: a real article, a redirect
into some other page, or nothing at all. A title that was a redirect or a redlink in Jan 2024 is
not a dedicated page, however it reads today. Writes data/<VERSION>/page_history.json.

Run: python3 pipeline/stage_1_fetch_the_frozen_list/fetch_article_history.py   (network; re-run only when the snapshot or the title set moves)
"""
import argparse, json, os, subprocess, sys, time, urllib.parse
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest

_ap = argparse.ArgumentParser()
_ap.add_argument('--version', required=True, metavar='NAME',
                 help='the dataset version to work in: data/<NAME>/ — e.g. mark_2026-09-22')
VERSION = _ap.parse_args().version
STARTED = manifest.now()
SNAPSHOT = '2024-01-26T03:23:06Z'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(ROOT, 'data', VERSION)
API = 'https://en.wikipedia.org/w/api.php'
PACE = float(os.environ.get('PAGES_PACE', 3))  # seconds between titles; the API throttles hard
UA = 'wikipedia-open-problems-audit/1.0 (research; contact via repository)'


def get(params):
    """One API call, backing off hard when the API says we are going too fast."""
    url = API + '?' + urllib.parse.urlencode({**params, 'format': 'json', 'formatversion': '2',
                                              'maxlag': '5'})
    for wait in (10, 30, 60, 120, 120, 120, 300, 300):
        r = subprocess.run(['curl', '-s', '-m', '60', '-H', f'User-Agent: {UA}', url],
                           capture_output=True, text=True)
        try:
            j = json.loads(r.stdout)
        except json.JSONDecodeError:
            print(f'  throttled, sleeping {wait}s', flush=True)
            time.sleep(wait)
            continue
        if 'error' in j and j['error'].get('code') in ('maxlag', 'ratelimited'):
            print(f'  {j["error"]["code"]}, sleeping {wait}s', flush=True)
            time.sleep(wait)
            continue
        return j
    raise SystemExit(f'API failed: {url}')


def at_snapshot(title):
    """(state, timestamp, target) for `title` as of SNAPSHOT."""
    j = get(dict(action='query', prop='revisions', titles=title, rvstart=SNAPSHOT, rvdir='older',
                 rvlimit=1, rvprop='timestamp|content', rvslots='main'))
    page = j['query']['pages'][0]
    if page.get('missing') or not page.get('revisions'):
        return 'absent', None, None
    rev = page['revisions'][0]
    text = rev['slots']['main'].get('content', '')
    if text.lstrip().lower().startswith('#redirect'):
        seg = text[text.lower().index('#redirect'):][:300]
        target = None
        if '[[' in seg and ']]' in seg:
            target = seg[seg.index('[[') + 2:seg.index(']]')].split('|')[0].split('#')[0].strip()
        return 'redirect', rev['timestamp'], target
    return 'article', rev['timestamp'], None


def created(title):
    j = get(dict(action='query', prop='revisions', titles=title, rvdir='newer', rvlimit=1,
                 rvprop='timestamp'))
    page = j['query']['pages'][0]
    if page.get('missing') or not page.get('revisions'):
        return None
    return page['revisions'][0]['timestamp']


# The titles come straight off the frozen page, through the same helper build.py uses for a
# problem's primary_wikilink — so the two cannot disagree and this script no longer waits on a
# build. (It used to read build's primary_links.json, which made the pipeline cyclic.)
from wikitext import primary_titles

PAGE = os.path.join(DATA_DIR, 'page.wiki')
if not os.path.exists(PAGE):
    raise SystemExit('no page.wiki — run pipeline/stage_1_fetch_the_frozen_list/fetch_list_revision.py first')
titles = sorted(set(primary_titles(open(PAGE, encoding='utf-8').read())))

OUT = os.path.join(DATA_DIR, 'page_history.json')
prior = json.load(open(OUT, encoding='utf-8'))['pages'] if os.path.exists(OUT) else {}
out = {t: prior[t] for t in titles if t in prior}


def save():
    json.dump(dict(snapshot=SNAPSHOT, fetched=time.strftime('%Y-%m-%d'),
                   pages={t: out[t] for t in titles if t in out}),
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


todo = [t for t in titles if t not in out]
print(f'{len(out)} cached, {len(todo)} to fetch')
for n, t in enumerate(todo, 1):
    state, ts, target = at_snapshot(t)
    # the creation date only adds anything when nothing stood at the title in Jan 2024
    out[t] = dict(snapshot_state=state, snapshot_rev=ts, redirect_target=target,
                  created=created(t) if state == 'absent' else None)
    if n % 10 == 0 or n == len(todo):
        save()
        print(f'{n}/{len(todo)}', flush=True)
    time.sleep(PACE)

save()
counts = {}
for r in out.values():
    counts[r['snapshot_state']] = counts.get(r['snapshot_state'], 0) + 1
print('wrote page_history.json', counts)

manifest.record(ROOT, VERSION, 'fetch', os.path.abspath(__file__),
                counts=dict(titles=len(out), fetched=len(todo), **counts),
                extra=dict(snapshot=SNAPSHOT, pace_seconds=PACE,
                           wrote='page_history.json'), started=STARTED)
