"""Find the year each problem was first posed.

One headless claude call per problem, resumable, in parallel. Writes one record per problem into
data/<VERSION>/year_posed/<key>.json, collected into year_posed.json, which merge_research.py
reads to fill year_introduced.

This is a lookup, not research: for most problems the year is stated outright in the lead or the
infobox of the problem's own Wikipedia article ("conjectured by Ott-Heinrich Keller in 1939"). The
prompt is built around that, and around the two ways it goes wrong — dating the paper that named
the problem rather than the one that posed it, and guessing when no source says.

A problem with no sourced year gets none. The dataset treats a missing year as a gap, and the site
omits the age charts rather than drawing them over a partial corpus, so a null costs nothing and a
wrong year costs a reader's trust.

  python3 pipeline/stage_5_date_each_problem/year_posed.py                  # all outstanding, 8 at a time
  python3 pipeline/stage_5_date_each_problem/year_posed.py --limit 20       # a pilot
  python3 pipeline/stage_5_date_each_problem/year_posed.py --only kakeya-conjecture
  python3 pipeline/stage_5_date_each_problem/year_posed.py --check          # validate and collect, run nothing
"""
import argparse, collections, concurrent.futures, hashlib, json, os, re, subprocess, sys, threading

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import limits, manifest
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version to work in: data/<NAME>/ — e.g. mark_2026-09-22')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--parallel', type=int, default=8)
ap.add_argument('--model', default='claude-haiku-5-5',
                help='exact model id, never an alias: an alias resolves to a different model over time, and a trial that records one cannot be read back. '
                     'Haiku 5.5, not 4.5: 4.5 ignores --effort and does not reason, and a literature year needs judging which paper first asked')
ap.add_argument('--effort', default='high', help='pinned so the run does not inherit the shell')
ap.add_argument('--subscription', action='store_true',
                help='bill the Claude Code subscription instead of the API key in .secrets.json')
ap.add_argument('--limit', type=int, help='run only the first N outstanding problems')
ap.add_argument('--only', nargs='+', metavar='KEY')
ap.add_argument('--check', action='store_true', help='validate and collect, run nothing')
ap.add_argument('--force', action='store_true',
                help='research again even though year_posed.json is already there')
args = ap.parse_args()
VERSION = args.version

DATA = os.path.join(ROOT, 'data', VERSION)
OUT = os.path.join(DATA, 'year_posed')
LOGS = os.path.join(OUT, 'logs')
BASES = ('wikipedia_infobox', 'wikipedia_lead', 'literature', 'unknown')

# ----------------------------------------------------------------------------------------------
# The prompt. One problem per run; everything the agent is told is here.
# ----------------------------------------------------------------------------------------------

SYSTEM = """\
You are establishing one fact about one mathematical problem: **the year it was first posed.**

Not the year it was solved, not the year it became famous, not the year of the survey you found it
in. The year someone first asked it.

## Where to look, in order

1. **The problem's own Wikipedia article.** Most of these state it plainly, either in the infobox
   (`Conjectured by`, `Conjectured in`) or in the first sentences of the lead: "conjectured by
   Ott-Heinrich Keller in 1939", "posed in 1955", "a 1966 problem of Erdős". If the article says
   it, you are done — quote it.
2. **The standard reference**, where Wikipedia does not say: the paper or letter the problem is
   attributed to, a survey that dates it, a problem collection (the Scottish Book, Erdős problem
   lists, Smale's list, the Kourovka Notebook).

## The two ways this goes wrong

**Dating the wrong event.** A problem is often named after someone who did not pose it, restated
decades later in the form the list gives, or first written down in a paper about something else.
Where the sources distinguish "first asked" from "first published in this form", take the earlier
and say so in `note`. Where a problem grew out of a body of work with no single asking, say that in
`note` and give the year the standard reference assigns, if there is one.

**Guessing.** A model will often half-remember a plausible year for a famous conjecture. Do not
write a year you cannot quote a source for. `basis: "unknown"` with `year: null` is a correct and
useful answer, and it is much better than a year that is nearly right: nobody downstream can tell a
recalled year from a sourced one once it is in the table.

A range or an approximation is not a year. "Late 1960s" is `year: null` with the phrase in `note`.
If a source says "c. 1988", record 1988 and set `approx` true.

## What to return

One JSON object, written to the path the prompt gives you, and nothing else.

```jsonc
{
  "key": "jacobian-conjecture",       // exactly as given
  "year": 1939,                       // the year, or null
  "approx": false,                    // true where the source hedges ("c. 1988", "around 1970")
  "basis": "wikipedia_lead",          // wikipedia_infobox | wikipedia_lead | literature | unknown
  "quote": "conjectured by Ott-Heinrich Keller in 1939",  // verbatim; null when year is null
  "url": "https://en.wikipedia.org/wiki/Jacobian_conjecture",
  "posed_by": "Ott-Heinrich Keller",  // as the source names them, or null
  "note": "",                         // disagreements between sources, or why there is no year
  "queries": ["..."],                 // every search you ran, verbatim
  "checked_on": "YYYY-MM-DD"
}
```

Two to four searches. Stop as soon as a source states the year."""


def prompt(p, out_path):
    lines = ['Find the year this problem was first posed.', '',
             f"- **key**: `{p['key']}`",
             f"- **statement, as Wikipedia words it**: {p['statement']}",
             f"- **field**: {p['field']}"]
    if p['subfield']:
        lines.append(f"- **subfield**: {p['subfield']}")
    if p['parent']:
        lines.append(f"- **parent**: this is a sub-case of `{p['parent']}` — {p['parent_statement']}."
                     " Date the sub-case if it has its own origin, the parent if it does not, and"
                     " say which in `note`.")
    lines += ['', f"Write the record to `{out_path}` and nothing else."]
    return '\n'.join(lines)


# ----------------------------------------------------------------------------------------------


record = lambda k: os.path.relpath(os.path.join(OUT, k + '.json'), ROOT)


def done(k):
    p = os.path.join(OUT, k + '.json')
    return os.path.exists(p) and os.path.getsize(p) > 0


def problems(revision):
    rows = parse_problem_keys(os.path.join(ROOT, 'data', VERSION, 'problem_keys.md'), revision)
    return {r['key']: r for r in rows if not r['is_grouping']}


def scraped():
    """Problems already dated mechanically by pipeline/stage_1_fetch_the_frozen_list/scrape_years.py.

    Those years were read straight off the article — an infobox field or a dating phrase in the
    lead — so there is nothing for an agent to add. They are skipped here and merged back in by
    check(), which writes both sources into one file with `source` saying which is which.
    """
    path = os.path.join(DATA, 'year_scraped.json')
    return json.load(open(path, encoding='utf-8')) if os.path.exists(path) else {}


def environment():
    """The API key from .secrets.json and nothing inherited, or with --subscription no key at all."""
    if args.subscription:
        # As judge.py does: strip every key and refuse if project settings could supply one, so a
        # run that says it used the subscription cannot have billed the key.
        env = {k: v for k, v in os.environ.items()
               if not k.startswith('ANTHROPIC') and not (k.startswith('CLAUDE') and k != 'CLAUDE_CONFIG_DIR')}
        assert not any('API_KEY' in k or 'AUTH_TOKEN' in k for k in env), 'an API key variable survived'
        for name in ('settings.json', 'settings.local.json'):
            path = os.path.join(ROOT, '.claude', name)
            if os.path.exists(path):
                s = json.load(open(path))
                if s.get('apiKeyHelper') or any(k.startswith('ANTHROPIC') for k in (s.get('env') or {})):
                    sys.exit(f'{os.path.relpath(path, ROOT)} could supply an API key — refusing to run')
        return env
    env = {k: v for k, v in os.environ.items()
           if not k.startswith('CLAUDE') and not k.startswith('ANTHROPIC')}
    secrets = os.path.join(ROOT, '.secrets.json')
    if not os.path.exists(secrets):
        sys.exit('no .secrets.json — put {"ANTHROPIC_API_KEY": "sk-ant-..."} there')
    key = json.load(open(secrets)).get('ANTHROPIC_API_KEY')
    if not key:
        sys.exit('.secrets.json has no ANTHROPIC_API_KEY')
    env['ANTHROPIC_API_KEY'] = key
    return env


STOP = threading.Event()
LIMITED = {}                                          # key -> the usage-limit message that stopped it
CHILDREN, LOCK = set(), threading.Lock()


def run_one(p):
    if STOP.is_set():
        return p['key'], None
    log_path = os.path.join(LOGS, p['key'] + '.log')
    log = open(log_path, 'a')                         # appended, so a retry keeps the last failure
    log.write(f'\n===== attempt started {manifest.now()} =====\n')
    log.flush()
    proc = subprocess.Popen(['claude', '-p', prompt(p, record(p['key'])),
                             '--append-system-prompt', SYSTEM,
                             '--model', args.model, '--effort', args.effort,
                             '--allowedTools', 'WebSearch', 'WebFetch', 'Write',
                             '--permission-mode', 'acceptEdits'],
                            cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    with LOCK:
        CHILDREN.add(proc)
    try:
        proc.wait()
    finally:
        with LOCK:
            CHILDREN.discard(proc)
        log.close()
    ok = done(p['key'])
    if not ok and (msg := limits.limit_message(log_path)):
        LIMITED[p['key']] = msg
        STOP.set()                                    # launch nothing more; it would fail the same way
    return p['key'], ok


def check(keys):
    records, bad = {}, []
    for k in [k for k in keys if k not in SCRAPED]:
        path = os.path.join(OUT, k + '.json')
        if not done(k):
            bad.append(f'{k}: no record')
            continue
        try:
            r = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            bad.append(f'{k}: unreadable ({e})')
            continue
        if r.get('key') != k:
            bad.append(f'{k}: record key is {r.get("key")!r}')
        if r.get('basis') not in BASES:
            bad.append(f'{k}: basis {r.get("basis")!r}')
        y = r.get('year')
        if y is not None:
            if not isinstance(y, int) or not -3000 < y <= 2026:
                bad.append(f'{k}: year {y!r}')
            if not (r.get('quote') and r.get('url')):
                bad.append(f'{k}: year with no quote and URL — an unsourced year is a guess')
            if r.get('basis') == 'unknown':
                bad.append(f'{k}: basis unknown but a year was given')
        elif r.get('basis') != 'unknown':
            bad.append(f'{k}: no year but basis {r.get("basis")!r}')
        if not r.get('queries'):
            bad.append(f'{k}: no queries recorded')
        records[k] = r
    for r in records.values():
        r.setdefault('source', 'agent')
    merged = dict(SCRAPED, **records)
    got = sum(1 for r in merged.values() if r.get('year') is not None)
    counts = collections.Counter(r.get('basis') for r in merged.values())
    print(f'\n{len(records)} agent records + {len(SCRAPED)} scraped = {len(merged)} of {len(keys)} '
          f'problems; {got} with a year  ' + '  '.join(f'{b}={counts[b]}' for b in BASES if counts[b]))
    for b in bad[:40]:
        print('  ' + b)
    if len(bad) > 40:
        print(f'  … and {len(bad) - 40} more')
    json.dump(merged, open(os.path.join(DATA, 'year_posed.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('-> ' + os.path.relpath(os.path.join(DATA, 'year_posed.json'), ROOT))
    return bad


ALL = problems(args.revision)
SCRAPED = scraped()

# A cache, not a stage to repeat. The year a problem was posed does not change, and the agents that
# find it are the expensive part of this script, so an existing year_posed.json is taken as done.
# --force researches again; --check rebuilds the file from what is already on disk, which is how a
# trial gets the scraped years without spending anything.
CACHE = os.path.join(DATA, 'year_posed.json')
if os.path.exists(CACHE) and not (args.force or args.check or args.only):
    n = len(json.load(open(CACHE, encoding='utf-8')))
    print(f'{os.path.relpath(CACHE, ROOT)} already has {n} of {len(ALL)} problems dated — nothing to do.')
    print('  --force to research them again, --check to rebuild the file from the records on disk.')
    sys.exit(0)
os.makedirs(LOGS, exist_ok=True)

if not args.check:
    ENV = environment()
    todo = [k for k in sorted(ALL) if not done(k) and k not in SCRAPED]
    if args.only:
        todo = [k for k in args.only if k in ALL]
        if miss := set(args.only) - set(todo):
            sys.exit('no such key: ' + ', '.join(sorted(miss)))
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(ALL)} problems; {len(SCRAPED)} already dated from their article; '
          f'{len(todo)} to run now, {args.parallel} at a time, model {args.model}')
    STARTED = manifest.now()
    failed, skipped = [], []

    def record_run(interrupted=False):
        # What produced these records: the exact model, the prompt's hash, the commit, the counts.
        # The prompt lives in this script, not a file, so its hash is taken of the text itself.
        manifest.record(ROOT, args.version, 'years', os.path.abspath(__file__),
                        args.model, args.effort, args.parallel,
                        prompt_path=None,
                        selection=dict(only=args.only, limit=args.limit, force=args.force),
                        counts=dict(problems=len(ALL), scraped=len(SCRAPED), ran=len(todo) - len(skipped),
                                    failed=len(failed), limited=len(LIMITED), not_started=len(skipped)),
                        started=STARTED,
                        extra=dict(billing='subscription' if args.subscription else 'api_key',
                                   prompt_sha256=hashlib.sha256(SYSTEM.encode()).hexdigest()[:16],
                                   failed=failed, limited=sorted(LIMITED), interrupted=interrupted,
                                   limit_message=next(iter(LIMITED.values()), None)))

    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (k, ok) in enumerate(pool.map(run_one, [ALL[k] for k in todo]), 1):
            if ok is None:
                skipped.append(k)
            elif k in LIMITED:
                print(f'{i:4}/{len(todo)}  LIMIT {k}', flush=True)
            else:
                if not ok:
                    failed.append(k)
                print(f'{i:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  {k}', flush=True)
    except KeyboardInterrupt:
        print('\ninterrupted — rerun the same command to resume')
        STOP.set()
        with LOCK:
            procs = list(CHILDREN)
        for p in procs:
            p.terminate()
        pool.shutdown(wait=True, cancel_futures=True)
        record_run(interrupted=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)
    if LIMITED:
        print(f'\nstopped at the usage limit ({next(iter(LIMITED.values()))}). '
              'Rerun the same command after the reset to resume.', flush=True)
    record_run()

sys.exit(1 if check(sorted(ALL)) else 0)
