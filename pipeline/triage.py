"""Run the triage pass: one headless claude call per problem, in parallel, resumable.

Reads the problem list out of problem_keys.md, sends each problem on its own to a cheap model
with TRIAGE_INSTRUCTIONS.md as the system prompt, and collects the records it writes into
triage/<revision>/triage.json.

Problems whose record already exists are skipped, so re-running retries only the failures:
delete the bad records and run it again.

  python3 pipeline/triage.py                        # all 462, 8 at a time
  python3 pipeline/triage.py --limit 20             # a pilot
  python3 pipeline/triage.py --only kakeya-conjecture bost-conjecture
  python3 pipeline/triage.py --check                # validate and collect, run nothing
"""
import argparse, collections, concurrent.futures, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDICTS = ('likely', 'possible', 'none', 'skip')

ap = argparse.ArgumentParser()
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--parallel', type=int, default=8)
ap.add_argument('--model', default='sonnet')
ap.add_argument('--limit', type=int, help='run only the first N outstanding problems')
ap.add_argument('--only', nargs='+', metavar='KEY', help='run only these keys')
ap.add_argument('--effort', default='low', help='pinned so the run does not inherit the shell')
ap.add_argument('--check', action='store_true', help='validate and collect, run nothing')
args = ap.parse_args()

BASE = os.path.join(ROOT, 'triage', args.revision)
OUT, LOGS = os.path.join(BASE, 'out'), os.path.join(BASE, 'logs')


def problems(revision):
    """The problems to triage: every bullet in the section except the article's own headings."""
    rows = parse_problem_keys(os.path.join(ROOT, 'problem_keys.md'), revision)
    return [r for r in rows if not r['is_grouping']]


def prompt(p):
    lines = ['Triage this one problem, following TRIAGE_INSTRUCTIONS.md.', '',
             f"- **key**: `{p['key']}`",
             f"- **statement**: {p['statement']}",
             f"- **field**: {p['field']}"]
    if p['subfield']:
        lines.append(f"- **subfield**: {p['subfield']}")
    if p['parent']:
        lines.append(f"- **parent**: sub of `{p['parent']}` — {p['parent_statement']}")
    lines += ['', f"Write the record to `{record(p['key'])}` and nothing else."]
    return '\n'.join(lines)


def record(key):
    return os.path.relpath(os.path.join(OUT, key + '.json'), ROOT)


def done(key):
    path = os.path.join(OUT, key + '.json')
    return os.path.exists(path) and os.path.getsize(path) > 0


def environment():
    """The subprocess environment: the API key from .secrets.json, and nothing inherited.

    ANTHROPIC_API_KEY is set here and the inherited CLAUDE_*/ANTHROPIC_* vars are dropped, so
    the run bills this key and the launching shell cannot change its behaviour (CLAUDE_EFFORT
    in particular would otherwise override --effort).

    Do NOT add --bare to force the key harder: it disables WebSearch, and the triage agent
    then falls back to curl, which is sandboxed. That produced 175 evidence-free records
    before it was caught.
    """
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


def run_one(p):
    log = open(os.path.join(LOGS, p['key'] + '.log'), 'w')
    subprocess.run(['claude', '-p', prompt(p),
                    '--append-system-prompt', INSTRUCTIONS,
                    '--model', args.model,
                    '--effort', args.effort,
                    '--allowedTools', 'WebSearch', 'WebFetch', 'Write',
                    '--permission-mode', 'acceptEdits'],
                   cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    log.close()
    return p['key'], done(p['key'])


def check(all_problems):
    """Validate every record, write the collected file, return the list of complaints."""
    records, bad = [], []
    for p in all_problems:
        key, path = p['key'], os.path.join(OUT, p['key'] + '.json')
        if not done(key):
            bad.append(f'{key}: no record')
            continue
        try:
            r = json.load(open(path))
        except Exception as e:
            bad.append(f'{key}: unreadable ({e})')
            continue
        if r.get('key') != key:
            bad.append(f'{key}: record key is {r.get("key")!r}')
        if r.get('verdict') not in VERDICTS:
            bad.append(f'{key}: verdict {r.get("verdict")!r}')
        if not r.get('queries'):              # a `none` with no queries is a check that never ran
            bad.append(f'{key}: no queries recorded')
        if r.get('verdict') in ('likely', 'possible') and not r.get('found'):
            bad.append(f'{key}: {r["verdict"]} with nothing in found')
        records.append(r)
    counts = collections.Counter(r.get('verdict') for r in records)
    print(f'\n{len(records)} of {len(all_problems)} records  ' +
          '  '.join(f'{v}={counts[v]}' for v in VERDICTS))
    for b in bad:
        print('  ' + b)
    json.dump(records, open(os.path.join(BASE, 'triage.json'), 'w'), indent=1, ensure_ascii=False)
    print('-> ' + os.path.relpath(os.path.join(BASE, 'triage.json'), ROOT))
    return bad


INSTRUCTIONS = open(os.path.join(ROOT, 'TRIAGE_INSTRUCTIONS.md')).read()
all_problems = problems(args.revision)
if not all_problems:
    sys.exit(f'no problems found for revision {args.revision} in problem_keys.md')
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

if not args.check:
    ENV = environment()
    todo = [p for p in all_problems if not done(p['key'])]
    if args.only:
        todo = [p for p in all_problems if p['key'] in set(args.only)]
        if missing := set(args.only) - {p['key'] for p in todo}:
            sys.exit('no such key: ' + ', '.join(sorted(missing)))
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(todo)} to run, {args.parallel} at a time, model {args.model}')
    with concurrent.futures.ThreadPoolExecutor(args.parallel) as pool:
        for i, (key, ok) in enumerate(pool.map(run_one, todo), 1):
            print(f'{i:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  {key}', flush=True)

sys.exit(1 if check(all_problems) else 0)
