"""Match the openai/math result families to the problems on the frozen list.

Step 2 of the OpenAI stage. index.py has already turned the repository into a fixed list of 372
families; this decides which of the 457 problems each one bears on, so that events.py knows which
manuscripts to read for which problem.

How it works, in one paragraph: the families are cut into batches of ten. Each batch goes to one
agent along with the whole problem list, and the agent writes back, for every family in its batch,
the problems it bears on (or an empty list). Matching is deliberately generous, because a family
missed here is never looked at again, while a wrong match is caught by events.py and the judge.
The agent works only from what it is given: it cannot search, and it writes one file.

What it writes, all under data/<version>/openai/:

  matches/batch-NNN.json   one per batch, the agent's answer, kept as written
  matches.json             every (family, problem) pair collected from the batches, plus two
                           lists for a human to look over: the name hints the agent did not
                           take up, and the families it matched to nothing

Resumable like the other agent stages: a batch whose answer exists and is complete is skipped, so
running the same command again retries only what failed. Bills the Claude Code subscription,
never an API key.

  python3 pipeline/stage_3_check_the_openai_repository/match.py --version will-2026-10-10-haiku
  python3 pipeline/stage_3_check_the_openai_repository/match.py --version V --limit 2   # try two batches
  python3 pipeline/stage_3_check_the_openai_repository/match.py --version V --check     # collect, run nothing
"""
import argparse, concurrent.futures, json, os, re, subprocess, sys, threading, unicodedata

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import limits, manifest
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROMPT = os.path.join(ROOT, 'pipeline', 'prompts', 'MATCH_OPENAI.md')

# The guesses the agent may give for how a family relates to a problem. They are hints for the
# passes that follow; the judge, not this step, decides scope.
RELATIONS = ('settles', 'case', 'bound', 'variant', 'other')


# ---------------------------------------------------------------------------------------------
# Arguments
# ---------------------------------------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version: reads data/<NAME>/openai/index.json, writes beside it')
ap.add_argument('--revision', default='2024-01', help='the list revision the problem keys belong to')
ap.add_argument('--model', default='claude-sonnet-5-5',
                help='exact model id, never an alias. Matching needs judgement more than search, '
                     'and there are only ~40 calls, so the stronger model is cheap here')
ap.add_argument('--effort', default='medium', help='pinned so the run does not inherit the shell')
ap.add_argument('--batch-size', type=int, default=10, help='families per agent')
ap.add_argument('--parallel', type=int, default=4)
ap.add_argument('--limit', type=int, help='run only the first N outstanding batches')
ap.add_argument('--check', action='store_true', help='validate and collect what exists, run nothing')
args = ap.parse_args()

DATA = os.path.join(ROOT, 'data', args.version)
OUT = os.path.join(DATA, 'openai')
ANSWERS, LOGS = os.path.join(OUT, 'matches'), os.path.join(OUT, 'logs', 'match')
INDEX = os.path.join(OUT, 'index.json')
if not os.path.exists(INDEX):
    sys.exit(f'no {os.path.relpath(INDEX, ROOT)} — run index.py first')
os.makedirs(ANSWERS, exist_ok=True)
os.makedirs(LOGS, exist_ok=True)


# ---------------------------------------------------------------------------------------------
# Inputs: the families (from the index) and the problems (from this version's problem_keys.md)
# ---------------------------------------------------------------------------------------------
index = json.load(open(INDEX, encoding='utf-8'))
manuscripts = {m['folder']: m for m in index['manuscripts']}
families = index['families']

# Grouping headings are not problems, so they are not in the denominator and not offered here.
problems = {r['key']: r for r in parse_problem_keys(os.path.join(DATA, 'problem_keys.md'), args.revision)
            if not r['is_grouping']}

# Batches are fixed by family number, so batch 7 is always the same ten families and a resumed
# run picks up exactly where the last one stopped.
batches = [families[i:i + args.batch_size] for i in range(0, len(families), args.batch_size)]


# ---------------------------------------------------------------------------------------------
# Name hints: a mechanical first guess, shown to the agent and checked against its answer
# ---------------------------------------------------------------------------------------------
# A problem's key is its name slugified ("zariski-multiplicity-conjecture"). Dropping the words
# every problem shares leaves its distinctive ones ("zariski", "multiplicity"); a family whose
# title or summary contains all of them is a hint. This is the check that found the misses in the
# first Haiku run, kept here so they can never be silently dropped: any hint the agent does not
# take up is listed in matches.json for a human to look at.
COMMON = set('''a an the of on in to for and or is are be there any all every many infinitely infinite
does do can which what how if with by as at its it that this than other given number numbers
conjecture conjectures problem problems hypothesis question exist exists existence value values find
finding determine theory graph graphs function functions set sets whose have has same most least
lowest largest smallest prime primes form type such'''.split())


def words(s):
    """Lower-case ASCII words, so "Erdős" and "erdos" compare equal."""
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return ' ' + re.sub(r'[^a-z0-9]+', ' ', s.replace("'", '').replace('’', '')) + ' '


def hints_for(family):
    text = words(family['title'] + ' ' + family['summary'])
    out = []
    for key in problems:
        distinctive = [t for t in key.split('-') if t not in COMMON and len(t) > 2 and not t.isdigit()]
        if distinctive and all(re.search(rf' {t}s? ', text) for t in distinctive):
            out.append(key)
    return out


HINTS = {f['num']: hints_for(f) for f in families}


# ---------------------------------------------------------------------------------------------
# The message each agent receives
# ---------------------------------------------------------------------------------------------
def problem_list():
    """Every problem as one line: its key, then its statement as the frozen list words it. A
    sub-problem carries its parent's key, because its statement often only makes sense with it."""
    lines = []
    for key, p in problems.items():
        parent = f" (sub-problem of `{p['parent']}`)" if p['parent'] else ''
        lines.append(f"- `{key}`{parent}: {p['statement']}")
    return '\n'.join(lines)


PROBLEM_LIST = problem_list()                       # the same for every batch, so built once


def family_block(f):
    """One family as the agent sees it: title, summary, and each manuscript's title and abstract.
    Earlier editions and withdrawn papers are left out; the current edition says the same and
    more, and a withdrawal is events.py's business."""
    lines = [f"### Family {f['num']}: {f['title']}", '', f['summary'], '']
    for folder in f['manuscripts']:
        m = manuscripts.get(folder, {})
        lines.append(f"- **{m.get('title', folder)}** — {m.get('abstract') or '(no abstract)'}")
    if HINTS[f['num']]:
        lines += ['', 'Name hints (mechanical, often wrong): ' + ', '.join(f'`{k}`' for k in HINTS[f['num']])]
    return '\n'.join(lines)


def answer_path(i):
    return os.path.join(ANSWERS, f'batch-{i:03d}.json')


def prompt(i, batch):
    return '\n'.join([
        'Match these families to the problems below, following MATCH_OPENAI.md.', '',
        f'This is batch {i}. It has {len(batch)} families: '
        + ', '.join(f['num'] for f in batch) + '. Every one must appear in your answer.', '',
        '## The families', '',
        '\n\n'.join(family_block(f) for f in batch), '',
        f'## The problems ({len(problems)})', '',
        PROBLEM_LIST, '',
        f'Write your answer to `{os.path.relpath(answer_path(i), ROOT)}` and write no other file.'])


# ---------------------------------------------------------------------------------------------
# Checking an answer
# ---------------------------------------------------------------------------------------------
def problems_with(i, batch):
    """What is wrong with batch i's answer, as a list of strings; empty means it is complete."""
    path = answer_path(i)
    if not os.path.exists(path):
        return ['no answer']
    try:
        a = json.load(open(path, encoding='utf-8'))
    except ValueError as e:
        return [f'unreadable JSON ({e})']
    bad = []
    given = [f['num'] for f in batch]
    got = [str(x.get('family')) for x in a.get('families') or []]
    # Every family accounted for, once: an omitted family would be a silent "no match".
    if sorted(got) != sorted(given):
        bad.append(f'families answered {got}, expected {given}')
    for x in a.get('families') or []:
        for mt in x.get('matches') or []:
            at = f"family {x.get('family')} -> {mt.get('problem')!r}"
            if mt.get('problem') not in problems:
                bad.append(f'{at}: not a key on the list')     # a typo'd key would match nothing
            if mt.get('relation') not in RELATIONS:
                bad.append(f'{at}: relation {mt.get("relation")!r}')
            if not mt.get('why'):
                bad.append(f'{at}: no why')
    return bad


def done(i, batch):
    return not problems_with(i, batch)


# ---------------------------------------------------------------------------------------------
# Running the agents (the same shape as research and judge)
# ---------------------------------------------------------------------------------------------
def environment():
    """The inherited environment minus anything that would bill an API key — as judge.py does.
    This step must run on the subscription, so it refuses to start if project settings could
    supply a key."""
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


STOP = threading.Event()        # set on an interrupt or at the usage limit: launch nothing more
LIMITED = {}                    # batch -> the usage-limit message that stopped it
CHILDREN, CHILDREN_LOCK = set(), threading.Lock()


def run_one(item):
    i, batch = item
    if STOP.is_set():
        return i, None                                  # never started
    # An incomplete answer from a previous attempt is moved into logs/, so the retry writes a
    # fresh file instead of tripping over the old one, and the old one is kept to look at.
    if os.path.exists(answer_path(i)):
        os.replace(answer_path(i), os.path.join(LOGS, f'batch-{i:03d}.incomplete-{manifest.now()[:19]}.json'))
    log_path = os.path.join(LOGS, f'batch-{i:03d}.log')
    log = open(log_path, 'a')                           # appended, so a retry keeps the last failure
    log.write(f'\n===== attempt started {manifest.now()} =====\n')
    log.flush()
    proc = subprocess.Popen(['claude', '-p', prompt(i, batch),
                             '--append-system-prompt', INSTRUCTIONS,
                             '--model', args.model,
                             '--effort', args.effort,
                             '--allowedTools', 'Write',     # no search: everything is in the message
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
    ok = done(i, batch)
    if not ok and (msg := limits.limit_message(log_path)):
        LIMITED[i] = msg
        STOP.set()
    return i, ok


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
# Collecting the answers into matches.json
# ---------------------------------------------------------------------------------------------
def collect():
    """Gather every complete batch into one file, and list what a human should look at."""
    pairs, nothing, complaints, answered = [], [], [], set()
    for i, batch in enumerate(batches):
        bad = problems_with(i, batch)
        if bad:
            complaints += [f'batch {i}: {b}' for b in bad]
            if bad == ['no answer']:
                continue
        try:
            a = json.load(open(answer_path(i), encoding='utf-8'))
        except (OSError, ValueError):
            continue
        for x in a.get('families') or []:
            answered.add(str(x.get('family')))
            ms = [mt for mt in x.get('matches') or [] if mt.get('problem') in problems]
            if not ms:
                nothing.append(str(x.get('family')))
            for mt in ms:
                pairs.append(dict(family=str(x['family']), problem=mt['problem'],
                                  relation=mt.get('relation'), why=mt.get('why'), batch=i))
    matched = {(p['family'], p['problem']) for p in pairs}
    # A hint the agent declined is not an error, but it is exactly where the last run went wrong,
    # so each one is listed for a person to confirm.
    declined = [dict(family=f, problem=k) for f, ks in HINTS.items() if f in answered
                for k in ks if (f, k) not in matched]
    out = dict(index_commit=index['repository']['commit'], model=args.model,
               families=len(families), batches=len(batches),
               batches_complete=sum(1 for i, b in enumerate(batches) if done(i, b)),
               pairs=pairs, problems_matched=len({p['problem'] for p in pairs}),
               hints_declined=declined, families_matching_nothing=nothing)
    json.dump(out, open(os.path.join(OUT, 'matches.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    print(f"\n{out['batches_complete']} of {len(batches)} batches complete")
    print(f"  {len(pairs)} (family, problem) pairs, covering {out['problems_matched']} problems")
    print(f"  {len(nothing)} families matched nothing; {len(declined)} name hints declined (listed in matches.json)")
    for c in complaints:
        print('  ' + c)
    print('-> ' + os.path.relpath(os.path.join(OUT, 'matches.json'), ROOT))
    return complaints


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------
INSTRUCTIONS = open(PROMPT, encoding='utf-8').read()

if not args.check:
    ENV = environment()
    todo = [(i, b) for i, b in enumerate(batches) if not done(i, b)]
    if args.limit:
        todo = todo[:args.limit]
    print(f'{len(families)} families in {len(batches)} batches of {args.batch_size}; '
          f'{len(todo)} to run now, {args.parallel} at a time, model {args.model}', flush=True)
    STARTED = manifest.now()
    failed, skipped = [], []

    def record_run(interrupted=False):
        manifest.record(ROOT, args.version, 'openai', os.path.abspath(__file__),
                        args.model, args.effort, args.parallel, prompt_path=PROMPT,
                        selection=dict(limit=args.limit, batch_size=args.batch_size),
                        counts=dict(batches=len(batches), ran=len(todo) - len(skipped),
                                    complete=sum(1 for i, b in enumerate(batches) if done(i, b)),
                                    failed=len(failed), limited=len(LIMITED), not_started=len(skipped)),
                        started=STARTED,
                        extra=dict(step='match', index_commit=index['repository']['commit'],
                                   failed=failed, limited=sorted(LIMITED), interrupted=interrupted,
                                   limit_message=next(iter(LIMITED.values()), None)))

    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for n, (i, ok) in enumerate(pool.map(run_one, todo), 1):
            if ok is None:
                skipped.append(i)
            elif i in LIMITED:
                print(f'{n:4}/{len(todo)}  LIMIT batch {i}', flush=True)
            else:
                if not ok:
                    failed.append(i)
                print(f'{n:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  batch {i}', flush=True)
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

sys.exit(1 if collect() else 0)
