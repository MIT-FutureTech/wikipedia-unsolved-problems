"""Run the deep dive: one headless claude call per problem, in parallel, resumable.

Sends every problem on its own to a strong model with DEEP_DIVE.md as the system prompt. Records
land in data/<version>/deepdive/out/<key>.json, inside the dataset folder the run builds.

There is no filter on what gets sent. A denominator where "open" might mean "nobody looked" is
worthless (DEEP_DIVE.md §1), so every problem is researched whether or not anything is expected
to have happened to it, and a well-evidenced "nothing happened" is the successful result for most
of them.

Problems whose record already exists are skipped, so re-running retries only the failures:
delete the bad records and run it again.

Every run belongs to a named version and writes only into data/<version>/deepdive/, so two runs
never share an output folder and a ruleset change never lands half-way through a set of records.
That folder is the same one build.py writes the finished dataset to: one run, one directory.

  python3 pipeline/stage_2_research_each_problem/deep_dive.py --version mark_2026-09-22 --limit 50
  python3 pipeline/stage_2_research_each_problem/deep_dive.py --version mark_2026-09-22 --only kakeya-conjecture
  python3 pipeline/stage_2_research_each_problem/deep_dive.py --version mark_2026-09-22 --check      # validate, run nothing
"""
import argparse, collections, concurrent.futures, json, os, random, re, subprocess, sys, threading

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The deep dive emits no codes of its own: `status`, `ai_role` and `resolution_direction` are the
# judging pass's, derived from these findings (DEEP_DIVE.md §7.1). The only closed vocabularies a
# record carries are these two.
KINDS = ('preprint', 'announcement', 'repository', 'journal', 'conference')
CONFIDENCE = ('high', 'medium', 'low')

ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version this run belongs to; its records land in '
                     'data/<NAME>/deepdive/ — e.g. mark_2026-09-22')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--parallel', type=int, default=4)
ap.add_argument('--model', default='claude-sonnet-5-5',
                help='exact model id, never an alias: an alias resolves to a different model over time, and a trial that records one cannot be read back')
ap.add_argument('--effort', default='medium', help='pinned so the run does not inherit the shell')
ap.add_argument('--limit', type=int, help='run only the first N outstanding problems, in key order')
ap.add_argument('--sample', type=int, metavar='N',
                help='run N problems drawn at random across the whole list, which --limit does not: '
                     'key order is alphabetical and clusters a trial into a handful of fields')
ap.add_argument('--seed', type=int, default=1,
                help='seed for --sample, so the same trial can be repeated or extended')
ap.add_argument('--only', nargs='+', metavar='KEY', help='run only these keys')
ap.add_argument('--check', action='store_true', help='validate and collect, run nothing')
args = ap.parse_args()

DATA = os.path.join(ROOT, 'data', args.version)
BASE = os.path.join(DATA, 'deepdive')
OUT, LOGS = os.path.join(BASE, 'out'), os.path.join(BASE, 'logs')

# A mistyped version would open a second run folder and re-research every problem at full cost, so
# the dataset folder has to exist already: fetch_list_revision.py creates it, before any research.
if not os.path.isdir(DATA):
    sys.exit(f'no data/{args.version}/ — run pipeline/stage_1_fetch_the_frozen_list/fetch_list_revision.py first, or check the '
             'name against the folders under data/')


def problems(revision):
    """{key: problem} for every bullet except the article's own headings."""
    rows = parse_problem_keys(os.path.join(ROOT, 'data', args.version, 'problem_keys.md'), revision)
    return {r['key']: r for r in rows if not r['is_grouping']}


def prompt(p):
    lines = ['Deep dive on this one problem, following DEEP_DIVE.md.', '',
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
    """The API key from .secrets.json, and nothing inherited.

    The inherited CLAUDE_*/ANTHROPIC_* vars are dropped so the launching shell cannot change the
    run's behaviour — CLAUDE_EFFORT in particular would otherwise override --effort.

    Do NOT add --bare to force the key harder: it disables WebSearch, and the agent then falls back
    to curl, which is sandboxed. In the retired triage pass that produced 175 evidence-free records
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


# Ctrl-C has to actually stop the run. ThreadPoolExecutor.map queues every task up front and
# shutdown() lets queued ones start, so an interrupt without this would keep launching agents
# that never saw the signal. STOP makes each worker refuse to start, and CHILDREN lets us end
# the ones already talking to the API.
STOP = threading.Event()
CHILDREN = set()
CHILDREN_LOCK = threading.Lock()


def run_one(p):
    if STOP.is_set():
        return p['key'], None                      # never started
    log = open(os.path.join(LOGS, p['key'] + '.log'), 'w')
    proc = subprocess.Popen(['claude', '-p', prompt(p),
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


def canonical(url):
    """A URL reduced to what makes it the same source.

    The scheme, a trailing slash, and arXiv's abs/pdf/html forms and version suffix all name one
    paper. Flagging `abs/2306.12713v2` as missing while `abs/2306.12713` sits in the source list
    is noise, and a check that cries wolf is one nobody reads.
    """
    u = url.strip().lower().split('://')[-1].rstrip('/')
    m = re.match(r'arxiv\.org/(?:abs|pdf|html)/(.+?)(?:\.pdf)?(?:v\d+)?$', u)
    return 'arxiv:' + m.group(1) if m else u


def cited(obj):
    """Every URL the record cites anywhere, to check against the source list (§7).

    The top-level `sources` list is skipped: it is the list being checked against, not a citation.
    """
    found = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                if v.startswith('http'):
                    found.add(v)
            elif k == 'sources' and isinstance(v, list):
                found |= {u for u in v if isinstance(u, str) and u.startswith('http')}
            else:
                found |= cited(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= cited(v)
    return found


def check(keys):
    """Validate every record on disk, write the collected file, return the complaints.

    Nothing here judges a record. The deep dive reports findings and the judging pass derives the
    codes from them (DEEP_DIVE.md §7.1), so there is no status to check a record against and no
    verdict to disagree with. A record is wrong only when it contradicts itself, omits something
    the prompt requires, or rests on a link it does not list.
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
        if r.get('confidence') not in CONFIDENCE:
            bad.append(f'{key}: confidence {r.get("confidence")!r}')
        if not (r.get('search') or {}).get('queries'):
            bad.append(f'{key}: no queries recorded')
        if not r.get('summary'):
            bad.append(f'{key}: no summary')
        # §5.1: one answer for the problem, written before any event was weighed. Per-event copies
        # drift towards whatever that event settled, which is the narrowing F13 exists to catch.
        if (r.get('events') or []) and not r.get('problem_asks'):
            bad.append(f'{key}: no problem_asks (§5.1)')
        # `nothing_found` is itself a finding (§4.1), so it has to mean what it says: a record
        # cannot both report that nothing happened and list something that did.
        events = r.get('events') or []
        if bool(r.get('nothing_found')) == bool(events):
            bad.append(f'{key}: nothing_found {r.get("nothing_found")!r} with {len(events)} events')
        seen = set()
        for i, ev in enumerate(events):
            at = f'{key}: event {ev.get("id") or i}'
            if not ev.get('id'):
                bad.append(f'{at}: no id')
            elif ev['id'] in seen:
                bad.append(f'{at}: duplicate id')
            seen.add(ev.get('id'))
            if not ev.get('date'):
                bad.append(f'{at}: no date')
            if ev.get('kind') not in KINDS:
                bad.append(f'{at}: kind {ev.get("kind")!r}')
            if not ev.get('sources'):
                bad.append(f'{at}: no sources')
            # §5.1 asks these separately from the record's `problem_asks`. A judge that cannot see
            # the gap between what the problem wants and what the event gives cannot score the scope.
            for f in ('delivers', 'remains'):
                if not ev.get(f):
                    bad.append(f'{at}: no {f} (§5.1)')
            if ev.get('precision') == 'year' and len(str(ev.get('date') or '')) > 4:
                bad.append(f'{at}: year precision but a month in the date (§5.1)')
            ai = ev.get('ai') or {}
            systems = ai.get('systems') or []
            if ai.get('none_found') and systems:
                bad.append(f'{at}: ai.none_found with {len(systems)} systems named (§5.4)')
            # §5.4: an attribution with no sentence from the authors behind it is the one thing
            # this pass may not produce, so a system missing its quote is a failed record.
            for s in systems:
                for f in ('name', 'what_it_did', 'basis_quote', 'quote_url'):
                    if not s.get(f):
                        bad.append(f'{at}: system {s.get("name") or "?"} with no {f} (§5.4)')
        # §7: a reader has to be able to get from any answer to the link behind it.
        listed = {canonical(s.get('url') or '') for s in (r.get('sources') or [])
                  if isinstance(s, dict)}
        for url in sorted(u for u in cited(r) if canonical(u) not in listed):
            bad.append(f'{key}: cited but not in sources: {url}')
        records.append(r)
    quiet = sum(1 for r in records if r.get('nothing_found'))
    evs = sum(len(r.get('events') or []) for r in records)
    named = sum(1 for r in records
                if any((e.get('ai') or {}).get('systems') for e in (r.get('events') or [])))
    conf = collections.Counter(r.get('confidence') for r in records)
    print(f'\n{len(records)} records validated of {len(ALL)} problems')
    print(f'  events:     {evs} across {len(records) - quiet} records,'
          f' {quiet} reporting nothing found')
    print(f'  ai:         {named} records name at least one system')
    print('  confidence: ' + '  '.join(f'{k}={conf[k]}' for k in CONFIDENCE if conf[k]))
    for b in bad:
        print('  ' + b)
    os.makedirs(BASE, exist_ok=True)
    json.dump(records, open(os.path.join(BASE, 'deepdive.json'), 'w'), indent=1, ensure_ascii=False)
    print('-> ' + os.path.relpath(os.path.join(BASE, 'deepdive.json'), ROOT))
    return bad


INSTRUCTIONS = open(os.path.join(ROOT, 'pipeline', 'prompts', 'DEEP_DIVE.md')).read()
ALL = problems(args.revision)
selected = sorted(ALL)
os.makedirs(OUT, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)

# The run log lives with the version it belongs to, so a run folder is self-contained: its
# records, its per-problem logs, its progress log, its collected file and the built dataset.
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
    if args.sample and args.limit:
        sys.exit('--sample and --limit both choose how many to run; pass one')
    if args.sample:
        # Sample the whole list, not just what is outstanding, so that resuming an interrupted
        # sample picks up the same problems rather than drawing a fresh set from the remainder.
        drawn = sorted(selected)
        random.Random(args.seed).shuffle(drawn)
        drawn = set(drawn[:args.sample])
        todo = [k for k in todo if k in drawn]
        say(f'sample of {args.sample} (seed {args.seed}) from {len(selected)} problems')
    if args.limit:
        todo = todo[:args.limit]
    say(f'{len(selected)} problems, {len(selected) - len(todo)} already recorded')
    say(f'{len(todo)} to run now, {args.parallel} at a time, model {args.model}')
    STARTED = manifest.now()
    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (key, ok) in enumerate(pool.map(run_one, [ALL[k] for k in todo]), 1):
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

if not args.check:
    # What produced these records: the exact model, the prompt's hash, the commit, the counts.
    manifest.record(ROOT, args.version, 'research', os.path.abspath(__file__),
                    args.model, args.effort, args.parallel,
                    prompt_path=os.path.join(ROOT, 'pipeline', 'prompts', 'DEEP_DIVE.md'),
                    selection=dict(only=args.only, limit=args.limit, sample=args.sample,
                                   seed=args.seed if args.sample else None),
                    counts=dict(problems=len(ALL), recorded=sum(1 for k in ALL if done(k)), ran=len(todo)),
                    started=STARTED)

sys.exit(1 if check(selected) else 0)
