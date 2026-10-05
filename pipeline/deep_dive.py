"""Run the deep dive: one headless claude call per flagged problem, in parallel, resumable.

Reads the triage records, selects the problems that earned a closer look, and sends each one on
its own to a strong model with DEEP_DIVE.md as the system prompt. Records land in
deepdive/<trial>/out/<key>.json.

Selection (this is the filter on pass one):
  every `likely` and every `possible`, plus --audit N randomly-drawn `none` problems, which are
  what measure the triage's miss rate. `skip` is never sent.

Problems whose record already exists are skipped, so re-running retries only the failures:
delete the bad records and run it again.

Every run belongs to a named trial and writes only into deepdive/<trial>/, so two runs never
share an output folder and a ruleset change never lands half-way through a set of records.

  python3 pipeline/deep_dive.py --trial mark_2026-09-22 --limit 50
  python3 pipeline/deep_dive.py --trial mark_2026-09-22 --audit 25   # + 25 sampled `none`
  python3 pipeline/deep_dive.py --trial mark_2026-09-22 --only kakeya-conjecture
  python3 pipeline/deep_dive.py --trial mark_2026-09-22 --check      # validate, run nothing
"""
import argparse, collections, concurrent.futures, json, os, random, subprocess, sys, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUSES = ('resolved', 'claimed', 'partial', 'progress', 'open_stale', 'open')
# `bound` is retired (24 Sep 2026): it named the kind of result, which `status` records, rather than
# who did the work. DEEP_DIVE.md 6.2 still defines it, so a new run can emit it and fail here.
AI_ROLES = ('generated', 'assisted', 'incident', 'none')

ap = argparse.ArgumentParser()
ap.add_argument('--trial', required=True, metavar='NAME',
                help='this run gets its own folder, deepdive/<NAME>/ — e.g. mark_2026-09-22')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--parallel', type=int, default=4)
ap.add_argument('--model', default='sonnet')
ap.add_argument('--effort', default='medium', help='pinned so the run does not inherit the shell')
ap.add_argument('--limit', type=int, help='run only the first N outstanding problems')
ap.add_argument('--only', nargs='+', metavar='KEY', help='run only these keys')
ap.add_argument('--audit', type=int, default=0, help='also send N randomly-drawn `none` problems')
ap.add_argument('--seed', type=int, default=1, help='seed for the audit sample, so it is reproducible')
ap.add_argument('--check', action='store_true', help='validate and collect, run nothing')
args = ap.parse_args()

TRIAGE = os.path.join(ROOT, 'triage', args.revision, 'out')
BASE = os.path.join(ROOT, 'deepdive', args.trial)
OUT, LOGS = os.path.join(BASE, 'out'), os.path.join(BASE, 'logs')


def problems(revision):
    """{key: problem} for every bullet except the article's own headings."""
    rows = parse_problem_keys(os.path.join(ROOT, 'problem_keys.md'), revision)
    return {r['key']: r for r in rows if not r['is_grouping']}


def triage_records():
    """The triage record per problem, or {} when no triage pass was run.

    Triage is an accelerator, not a gate: it gives each agent a head start (DEEP_DIVE.md 2.2) and
    its verdicts are worth measuring against the findings, but the deep dive researches every
    problem either way. Without it, every problem is selected and no record is passed through.
    """
    if not os.path.isdir(TRIAGE):
        print(f'no triage records in {os.path.relpath(TRIAGE, ROOT)} — researching every problem, '
              'with no triage head start')
        return {}
    out = {}
    for f in sorted(os.listdir(TRIAGE)):
        if f.endswith('.json'):
            r = json.load(open(os.path.join(TRIAGE, f)))
            out[f[:-5]] = r
    return out


def selection(triage):
    """The filter on pass one: everything flagged, plus a reproducible sample of `none`.

    With no triage to filter on, every problem is selected.
    """
    if not triage:
        return sorted(ALL)
    flagged = [k for k, r in sorted(triage.items()) if r.get('verdict') in ('likely', 'possible')]
    if args.audit:
        pool = sorted(k for k, r in triage.items() if r.get('verdict') == 'none')
        random.Random(args.seed).shuffle(pool)
        flagged += pool[:args.audit]
    return flagged


def prompt(p, t):
    lines = ['Deep dive on this one problem, following DEEP_DIVE.md.', '',
             f"- **key**: `{p['key']}`",
             f"- **statement**: {p['statement']}",
             f"- **field**: {p['field']}"]
    if p['subfield']:
        lines.append(f"- **subfield**: {p['subfield']}")
    if p['parent']:
        lines.append(f"- **parent**: sub of `{p['parent']}` — {p['parent_statement']}")
    if t:
        lines += ['', 'The triage record for this problem (§2.2 — a pointer, not a finding):', '',
                  '```json', json.dumps(t, indent=1, ensure_ascii=False), '```']
    else:
        lines += ['', 'No triage was run for this problem: there is no record to start from, and '
                  'nothing in §2.2 applies. Search it from the statement.']
    lines += ['', f"Write the record to `{record(p['key'])}` and nothing else."]
    return '\n'.join(lines)


def record(key):
    return os.path.relpath(os.path.join(OUT, key + '.json'), ROOT)


def done(key):
    path = os.path.join(OUT, key + '.json')
    return os.path.exists(path) and os.path.getsize(path) > 0


def environment():
    """The API key from .secrets.json, and nothing inherited (see triage.py for why not --bare)."""
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


# Ctrl-C has to actually stop the run. ThreadPoolExecutor.map queues every task up front and
# shutdown() lets queued ones start, so an interrupt without this would keep launching agents
# that never saw the signal. STOP makes each worker refuse to start, and CHILDREN lets us end
# the ones already talking to the API.
STOP = threading.Event()
CHILDREN = set()
CHILDREN_LOCK = threading.Lock()


def run_one(job):
    p, t = job
    if STOP.is_set():
        return p['key'], None                      # never started
    log = open(os.path.join(LOGS, p['key'] + '.log'), 'w')
    proc = subprocess.Popen(['claude', '-p', prompt(p, t),
                             '--append-system-prompt', INSTRUCTIONS,
                             '--model', args.model,
                             '--effort', args.effort,
                             '--allowedTools', 'WebSearch', 'WebFetch', 'Write',
                             '--permission-mode', 'acceptEdits'],
                            cwd=ROOT, env=ENV, stdout=log, stderr=subprocess.STDOUT)
    with CHILDREN_LOCK:
        CHILDREN.add(proc)
    try:
        proc.wait()
    finally:
        with CHILDREN_LOCK:
            CHILDREN.discard(proc)
        log.close()
    return p['key'], done(p['key'])


def stop_everything():
    STOP.set()
    with CHILDREN_LOCK:
        procs = list(CHILDREN)
    for proc in procs:
        proc.terminate()
    for proc in procs:
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def check(keys, triage):
    """Validate every record on disk, write the collected file, return the complaints.

    `keys` is only the set a run was *expected* to produce, and it is reported against separately.
    Validation itself covers every record in OUT, because the selection is a filter on which
    problems get researched, not on which results deserve checking: the triage that builds it
    misses real movement (AUDIT.md §2), and the records it passes over were silently never
    validated by anything.
    """
    records, bad = [], []
    present = sorted(k for k in ALL if done(k))
    for key in sorted(set(keys) - set(present)):
        bad.append(f'{key}: no record')
    for key in present:
        path = os.path.join(OUT, key + '.json')
        try:
            r = json.load(open(path))
        except Exception as e:
            bad.append(f'{key}: unreadable ({e})')
            continue
        if r.get('key') != key:
            bad.append(f'{key}: record key is {r.get("key")!r}')
        if r.get('status') not in STATUSES:
            bad.append(f'{key}: status {r.get("status")!r}')
        if r.get('ai_role') not in AI_ROLES:
            bad.append(f'{key}: ai_role {r.get("ai_role")!r}')
        if r.get('status') not in (None, 'open') and not r.get('status_sources'):
            bad.append(f'{key}: {r.get("status")} with no status_sources')
        if r.get('ai_role') not in (None, 'none') and not (r.get('ai') or {}).get('basis_quote'):
            bad.append(f'{key}: ai_role {r.get("ai_role")} with no basis_quote (§6.2)')
        if not (r.get('search') or {}).get('queries'):
            bad.append(f'{key}: no queries recorded')
        if r.get('status') in ('resolved', 'claimed', 'partial') and not r.get('resolution_direction'):
            bad.append(f'{key}: {r.get("status")} with no resolution_direction (§6.4)')
        if r.get('no_change_found') and r.get('status') != 'open':
            bad.append(f'{key}: no_change_found with status {r.get("status")}')
        ev = r.get('event') or {}
        if ev.get('date') and ev.get('precision') == 'year' and len(str(ev['date'])) > 4:
            bad.append(f'{key}: year precision but a month in the date (§6.3)')
        # An event before the frozen revision cannot be a change since the frozen revision. Only
        # `open_stale` (a pre-snapshot resolution the list never caught up with) and `open` (the
        # work is a note on a problem that did not move) may rest on one.
        if ev.get('predates_frozen_revision') is True and r.get('status') not in ('open_stale', 'open'):
            bad.append(f'{key}: status {r.get("status")} on an event predating the frozen revision (§6.1)')
        records.append(r)
    st = collections.Counter(r.get('status') for r in records)
    ai = collections.Counter(r.get('ai_role') for r in records)
    extra = len(present) - len(set(keys) & set(present))
    print(f'\n{len(records)} records validated of {len(ALL)} problems'
          f' ({len(set(keys) & set(present))} of the {len(keys)} selected'
          f'{f", plus {extra} outside the selection" if extra else ""})')
    print('  status: ' + '  '.join(f'{k}={st[k]}' for k in STATUSES if st[k]))
    print('  ai:     ' + '  '.join(f'{k}={ai[k]}' for k in AI_ROLES if ai[k]))
    for b in bad:
        print('  ' + b)
    os.makedirs(BASE, exist_ok=True)
    json.dump(records, open(os.path.join(BASE, 'deepdive.json'), 'w'), indent=1, ensure_ascii=False)
    print('-> ' + os.path.relpath(os.path.join(BASE, 'deepdive.json'), ROOT))
    return bad


INSTRUCTIONS = open(os.path.join(ROOT, 'DEEP_DIVE.md')).read()
ALL = problems(args.revision)
TRI = triage_records()
missing = [k for k in TRI if k not in ALL]
if missing:
    sys.exit('triage records with no matching problem: ' + ', '.join(missing[:5]))
selected = selection(TRI)
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

# The run log lives with the trial it belongs to, so a trial folder is self-contained: its
# records, its per-problem logs, its progress log and its collected file.
RUN_LOG = open(os.path.join(BASE, 'run.log'), 'a')


def say(line):
    print(line, flush=True)
    RUN_LOG.write(line + '\n')
    RUN_LOG.flush()


if not args.check:
    ENV = environment()
    todo = [k for k in selected if not done(k)]
    if args.only:
        todo = [k for k in args.only if k in ALL]
        if bad := set(args.only) - set(todo):
            sys.exit('no such key: ' + ', '.join(sorted(bad)))
    if args.limit:
        todo = todo[:args.limit]
    v = collections.Counter(TRI[k]['verdict'] for k in todo if k in TRI) or {'untriaged': len(todo)}
    say(f'{len(selected)} selected of {len(TRI)} triaged '
          f'({sum(1 for k in selected if TRI[k]["verdict"] == "likely")} likely, '
          f'{sum(1 for k in selected if TRI[k]["verdict"] == "possible")} possible, '
          f'{sum(1 for k in selected if TRI[k]["verdict"] == "none")} audit)')
    say(f'{len(todo)} to run now {dict(v)}, {args.parallel} at a time, model {args.model}')
    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (key, ok) in enumerate(pool.map(run_one, [(ALL[k], TRI[k]) for k in todo]), 1):
            if ok is None:
                continue                           # skipped after the interrupt
            say(f'{i:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  {key}')
    except KeyboardInterrupt:
        say('\ninterrupted — stopping agents in flight; rerun the same command to resume')
        stop_everything()
        pool.shutdown(wait=True, cancel_futures=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)

sys.exit(1 if check(selected, TRI) else 0)
