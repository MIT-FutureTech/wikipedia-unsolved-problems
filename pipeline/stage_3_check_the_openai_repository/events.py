"""Turn each (family, problem) match into an event in the research schema.

Step 3 of the OpenAI stage. match.py said which families bear on which problems; this writes,
for every match, the event the judge needs: what the manuscripts claim, what that delivers for
the problem, what remains, and the facts around it. The result has the same shape as an event a
research agent writes (DEEP_DIVE.md §7), so the judge scores it the same way.

The work is split by who can be trusted with what:

  the agent writes what needs reading   what_happened, delivers, remains, direction, object,
                                        conditional_on, doubts, readme_exception, and whether
                                        the match holds up at all
  this script fills in the rest         the date, sources, the AI quote, the compute, the Lean
                                        status, withdrawals and editions — all read off the
                                        index, so no agent retypes a fact the repository states

One agent per matched family. It is given the TeX source of the family's current manuscripts (a
short list of local files it may read and nothing else), the family's Lean scope, and every
problem it was matched to. It cannot search, and it writes one file.

What it writes, under data/<version>/openai/:

  events/family-NNN.json   one per family, the agent's answer, kept as written
  events.json              every event, assembled in the research schema and keyed by problem,
                           plus the matches the agents rejected and why — combine.py reads this

Resumable, stops at the usage limit, subscription only, like every other agent stage.

  python3 pipeline/stage_3_check_the_openai_repository/events.py --version will-2026-10-10-haiku --limit 3
  python3 pipeline/stage_3_check_the_openai_repository/events.py --version will-2026-10-10-haiku
  python3 pipeline/stage_3_check_the_openai_repository/events.py --version V --check   # assemble, run nothing
"""
import argparse, concurrent.futures, datetime, json, os, re, subprocess, sys, threading

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import limits, manifest
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT = os.path.join(ROOT, 'pipeline', 'prompts', 'OPENAI_EVENTS.md')
SOURCE = os.path.join(ROOT, 'sources', 'openai-math')        # the pinned clone index.py read


# ---------------------------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--model', default='claude-haiku-5-5',
                help='exact model id, never an alias. Reading a handful of local files is a smaller '
                     'job than open research, so the fast model is enough')
ap.add_argument('--effort', default='high', help='pinned so the run does not inherit the shell')
ap.add_argument('--parallel', type=int, default=6)
ap.add_argument('--only', nargs='+', metavar='FAMILY', help='run only these family numbers, e.g. 059 162')
ap.add_argument('--limit', type=int, help='run only the first N outstanding families')
ap.add_argument('--check', action='store_true', help='validate and assemble what exists, run nothing')
args = ap.parse_args()

DATA = os.path.join(ROOT, 'data', args.version)
OUT = os.path.join(DATA, 'openai')
ANSWERS, LOGS = os.path.join(OUT, 'events'), os.path.join(OUT, 'logs', 'events')
for need in ('index.json', 'matches.json'):
    if not os.path.exists(os.path.join(OUT, need)):
        sys.exit(f'no data/{args.version}/openai/{need} — run index.py and match.py first')
os.makedirs(ANSWERS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)


# ---------------------------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------------------------
index = json.load(open(os.path.join(OUT, 'index.json'), encoding='utf-8'))
matches = json.load(open(os.path.join(OUT, 'matches.json'), encoding='utf-8'))
FAMILIES = {f['num']: f for f in index['families']}
MANUSCRIPTS = {m['folder']: m for m in index['manuscripts']}
AI = index['ai_statement']
COMMIT = index['repository']['commit']

# The clone has to be the commit the index describes, or the files an agent reads could differ
# from the ones the index dated and linked.
head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=SOURCE, capture_output=True, text=True).stdout.strip()
if head != COMMIT:
    sys.exit(f'the clone is at {head[:9]} but the index was built at {COMMIT[:9]}; re-run index.py')

problems = {r['key']: r for r in parse_problem_keys(os.path.join(DATA, 'problem_keys.md'), args.revision)
            if not r['is_grouping']}

# family -> the matches for it, in the order match.py found them
by_family = {}
for p in matches['pairs']:
    by_family.setdefault(p['family'], []).append(p)


def problem_asks(key):
    """The research record's own unpacking of what the problem asks, where it wrote one."""
    path = os.path.join(DATA, 'deepdive', 'out', key + '.json')
    try:
        return json.load(open(path, encoding='utf-8')).get('problem_asks')
    except (OSError, ValueError):
        return None


# ---------------------------------------------------------------------------------------------
# What the agent may read: each current manuscript's main TeX file
# ---------------------------------------------------------------------------------------------
def main_tex(folder):
    """The TeX file that holds the paper, found by its \\documentclass. Section files are \\input
    from it, so the agent is also allowed to read anything under the folder's build/ directory."""
    build = os.path.join(SOURCE, 'preprints', folder, 'build')
    if not os.path.isdir(build):
        return None
    for root, _, files in os.walk(build):
        for f in sorted(files):
            if f.endswith('.tex'):
                path = os.path.join(root, f)
                if '\\documentclass' in open(path, encoding='utf-8', errors='replace').read(4000):
                    return os.path.relpath(path, ROOT)
    return None


def current_manuscripts(family):
    """The family's manuscripts as listed now: earlier editions and withdrawals are not read,
    though a withdrawal is still reported on the event."""
    return [MANUSCRIPTS[f] for f in family['manuscripts'] if f in MANUSCRIPTS]


# ---------------------------------------------------------------------------------------------
# The message each agent receives
# ---------------------------------------------------------------------------------------------
def answer_path(num):
    return os.path.join(ANSWERS, f'family-{num}.json')


def prompt(num):
    f = FAMILIES[num]
    lines = ['Describe what this family of manuscripts claims about each problem below, following OPENAI_EVENTS.md.', '',
             f"## Family {num}: {f['title']}", '', f['summary'], '', '### The manuscripts', '']
    for m in current_manuscripts(f):
        tex = main_tex(m['folder'])
        lines.append(f"- **{m['title']}**" + (f" — withdrawn on {m['withdrawn']}" if m['withdrawn'] else ''))
        lines.append(f"  Abstract: {m['abstract'] or '(none)'}")
        lines.append(f"  Read: `{tex}`" + ' (and the files it \\inputs, under the same build/ folder)' if tex
                     else f"  No TeX source; read the PDF: `{m['pdf']}`")
    if f.get('lean'):
        lines += ['', '### What the Lean formalisation covers, as the repository states it', '', f['lean']['scope'] or '(no scope given)']
    lines += ['', '### The problems this family was matched to', '']
    for p in by_family[num]:
        prob = problems[p['problem']]
        lines.append(f"- `{p['problem']}` — {prob['statement']}")
        if prob['parent']:
            lines.append(f"  (a sub-problem of: {prob['parent_statement']})")
        if asks := problem_asks(p['problem']):
            lines.append(f"  problem_asks: {asks}")
        lines.append(f"  The matching pass said ({p['relation']}): {p['why']}")
    lines += ['', f'Write your answer to `{os.path.relpath(answer_path(num), ROOT)}` and write no other file.']
    return '\n'.join(lines)


def allowed_tools(num):
    """Read only inside this family's manuscript folders, and write only the answer."""
    folders = [m['folder'] for m in current_manuscripts(FAMILIES[num])]
    return [f'Read(sources/openai-math/preprints/{d}/**)' for d in folders] + ['Write']


# ---------------------------------------------------------------------------------------------
# Checking an answer
# ---------------------------------------------------------------------------------------------
NEEDED = ('what_happened', 'delivers', 'remains', 'direction')


def problems_with(num):
    path = answer_path(num)
    if not os.path.exists(path):
        return ['no answer']
    try:
        a = json.load(open(path, encoding='utf-8'))
    except ValueError as e:
        return [f'unreadable JSON ({e})']
    bad = []
    want = sorted(p['problem'] for p in by_family[num])
    got = sorted(e.get('problem') for e in a.get('entries') or [])
    if got != want:                                   # every match answered, once
        bad.append(f'problems answered {got}, expected {want}')
    for e in a.get('entries') or []:
        at = f"family {num} -> {e.get('problem')}"
        if e.get('relevant') is False:
            if not e.get('not_relevant_because'):
                bad.append(f'{at}: rejected with no reason')
            continue
        if e.get('relevant') is not True:
            bad.append(f'{at}: relevant {e.get("relevant")!r}')
        for k in NEEDED:
            if not e.get(k):
                bad.append(f'{at}: no {k}')
        if not isinstance(e.get('readme_exception'), bool):
            bad.append(f'{at}: readme_exception {e.get("readme_exception")!r}')
    return bad


def done(num):
    return not problems_with(num)


# ---------------------------------------------------------------------------------------------
# Assembling an event: the agent's reading, plus the facts the index already holds
# ---------------------------------------------------------------------------------------------
TODAY = datetime.date.today()


def event(num, e):
    f = FAMILIES[num]
    ms = current_manuscripts(f)
    first = min((m['first_public'] for m in ms if m['first_public']), default=index['repository']['first_public'])
    withdrawn = [m for m in ms if m['withdrawn']]
    editions = [ed for m in ms for ed in m['editions']]
    # The repository's own attribution, quoted. A family the README names as an exception still
    # came from the model, but by a different procedure, so it quotes the exception instead.
    quote = AI['exceptions'] if e.get('readme_exception') else AI['procedure']
    lean = f.get('lean')
    days = (TODAY - datetime.date.fromisoformat(first)).days
    return {
        'id': f'openai-math-{num}',
        'what_happened': e['what_happened'],
        'date': first, 'precision': 'day',
        'kind': 'repository',
        'predates_frozen_revision': False,
        'revisions': ('; '.join(filter(None, [
            f"{len(editions)} earlier edition(s) kept in the repository: " + ', '.join(editions) if editions else None,
            'withdrawn: ' + ', '.join(f"{m['title']} on {m['withdrawn']}" for m in withdrawn) if withdrawn else None]))
            or None),
        'delivers': e['delivers'],
        'remains': e['remains'],
        'checked_by': [],
        # Not established by this stage: nobody has searched for outside engagement here, so this
        # is null rather than a claim that none exists.
        'no_engagement_found': None,
        'time_since_posted': f'{days} days',
        'machine_checked': ({'system': 'Lean 4', 'sorry_free': None,      # not built here
                             'url': f"https://github.com/openai/math/blob/{COMMIT}/{lean['doc']}",
                             'scope': lean['scope'],
                             'theorems': [t for r in lean['results'] for t in r['theorems']]}
                            if lean else None),
        'directly_checkable': None,
        'doubts': '; '.join(filter(None, [e.get('doubts'),
                                          f"conditional on: {e['conditional_on']}" if e.get('conditional_on') else None])) or None,
        'later_work_cites_it': None,
        'withdrawn': ({'what': ', '.join(m['title'] for m in withdrawn), 'date': withdrawn[0]['withdrawn'],
                       'by': 'author', 'sources': [m['url'] for m in withdrawn]}
                      if withdrawn and len(withdrawn) == len(ms) else None),
        'direction': e['direction'],
        'object': e.get('object'),
        'people': [],                                  # the repository credits no human author
        'ai': {
            'none_found': False,
            'systems': [{'name': 'an unreleased internal OpenAI model',
                         'what_it_did': 'produced the manuscripts, per the repository README',
                         'basis_quote': quote, 'quote_url': AI['url']}],
            'disclosed_cost': AI.get('compute'),
            'sources': [AI['url']],
        },
        'sources': [m['url'] for m in ms] + [AI['url']]
                   + ([f"https://github.com/openai/math/blob/{COMMIT}/{lean['doc']}"] if lean else []),
        # Not part of the research schema: lets combine.py and a reader tell where this came from.
        'origin': {'stage': 'openai', 'family': num, 'family_title': f['title'],
                   'repository_commit': COMMIT, 'read': e.get('read') or []},
    }


def assemble():
    by_problem, rejected, complaints = {}, [], []
    for num in sorted(by_family):
        bad = problems_with(num)
        if bad:
            complaints += [f'family {num}: {b}' for b in bad]
            continue                                   # only a complete answer is used
        for e in json.load(open(answer_path(num), encoding='utf-8'))['entries']:
            if e.get('relevant') is False:
                rejected.append(dict(family=num, problem=e['problem'], because=e['not_relevant_because']))
            else:
                by_problem.setdefault(e['problem'], []).append(event(num, e))
    out = dict(index_commit=COMMIT, model=args.model, events=by_problem, rejected=rejected,
               families_complete=sum(1 for n in by_family if done(n)), families=len(by_family))
    json.dump(out, open(os.path.join(OUT, 'events.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    n = sum(len(v) for v in by_problem.values())
    print(f"\n{out['families_complete']} of {len(by_family)} matched families complete")
    print(f'  {n} events across {len(by_problem)} problems; {len(rejected)} matches rejected on reading')
    for c in complaints:
        print('  ' + c)
    print('-> ' + os.path.relpath(os.path.join(OUT, 'events.json'), ROOT))
    return complaints


# ---------------------------------------------------------------------------------------------
# Running the agents (the same shape as match.py)
# ---------------------------------------------------------------------------------------------
def environment():
    """The inherited environment minus anything that would bill an API key, as judge.py does."""
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


STOP = threading.Event()
LIMITED = {}
CHILDREN, CHILDREN_LOCK = set(), threading.Lock()


def run_one(num):
    if STOP.is_set():
        return num, None
    # An earlier answer is moved into logs/ first (incomplete, or being redone with --only), so the
    # agent writes a fresh file and the old one is kept to look at.
    if os.path.exists(answer_path(num)):
        os.replace(answer_path(num), os.path.join(LOGS, f'family-{num}.previous-{manifest.now()[:19]}.json'))
    log_path = os.path.join(LOGS, f'family-{num}.log')
    log = open(log_path, 'a')
    log.write(f'\n===== attempt started {manifest.now()} =====\n')
    log.flush()
    proc = subprocess.Popen(['claude', '-p', prompt(num),
                             '--append-system-prompt', INSTRUCTIONS,
                             '--model', args.model,
                             '--effort', args.effort,
                             '--allowedTools', *allowed_tools(num),
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
    ok = done(num)
    if not ok and (msg := limits.limit_message(log_path)):
        LIMITED[num] = msg
        STOP.set()
    return num, ok


def stop_everything():
    STOP.set()
    with CHILDREN_LOCK:
        procs = list(CHILDREN)
    for p in procs:
        p.terminate()
    for p in procs:
        try:
            p.wait(timeout=10)
        except subprocess.TimeoutExpired:
            p.kill()


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
INSTRUCTIONS = open(PROMPT, encoding='utf-8').read()

if not args.check:
    if matches['batches_complete'] < matches['batches']:
        sys.exit(f"match.py has finished {matches['batches_complete']} of {matches['batches']} batches; "
                 'finish matching first, or the families it has not reached get no events')
    ENV = environment()
    scope = sorted(by_family) if not args.only else [n for n in args.only if n in by_family]
    todo = list(scope) if args.only else [n for n in scope if not done(n)]
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(by_family)} matched families; {len(todo)} to run now, {args.parallel} at a time, '
          f'model {args.model}', flush=True)
    STARTED = manifest.now()
    failed, skipped = [], []

    def record_run(interrupted=False):
        manifest.record(ROOT, args.version, 'openai', os.path.abspath(__file__),
                        args.model, args.effort, args.parallel, prompt_path=PROMPT,
                        selection=dict(only=args.only, limit=args.limit),
                        counts=dict(families=len(by_family), ran=len(todo) - len(skipped),
                                    complete=sum(1 for n in by_family if done(n)),
                                    failed=len(failed), limited=len(LIMITED), not_started=len(skipped)),
                        started=STARTED,
                        extra=dict(step='events', index_commit=COMMIT, failed=failed,
                                   limited=sorted(LIMITED), interrupted=interrupted,
                                   limit_message=next(iter(LIMITED.values()), None)))

    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for n, (num, ok) in enumerate(pool.map(run_one, todo), 1):
            if ok is None:
                skipped.append(num)
            elif num in LIMITED:
                print(f'{n:4}/{len(todo)}  LIMIT family {num}', flush=True)
            else:
                if not ok:
                    failed.append(num)
                print(f'{n:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  family {num}', flush=True)
    except KeyboardInterrupt:
        print('\ninterrupted — stopping agents in flight; rerun the same command to resume')
        stop_everything()
        pool.shutdown(wait=True, cancel_futures=True)
        record_run(interrupted=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)
    if LIMITED:
        print(f'\nstopped at the usage limit ({next(iter(LIMITED.values()))}). '
              'Rerun the same command after the reset to resume.', flush=True)
    record_run()

sys.exit(1 if assemble() else 0)
