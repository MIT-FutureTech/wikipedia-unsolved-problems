"""Run the judging pass: one headless claude call per research record, in parallel, resumable.

Each agent gets JUDGE.md as its system prompt and one deep-dive record, and writes a small verdict:
its answers, the field changes, and a correction entry per change. This script then writes the
corrected copy itself, so the copy is the original record plus exactly those changes — nothing the
agent retyped. The originals in deepdive/<trial>/out/ are never touched.

  deepdive/<trial>/judged/verdicts/<key>.json      the agent's verdict
  deepdive/<trial>/judged/out/<key>.json           the corrected copy
  deepdive/<trial>/judged-calibration/...          the same, for --calibrate

Runs on the Claude Code subscription: any ANTHROPIC_API_KEY is removed from the environment, so
each call uses the logged-in account (deep_dive.py and triage.py bill an API key instead).

--calibrate judges the records a human already corrected, as they stood before any correction
(their committed versions in git), and --score compares those verdicts with the human calls.

  python3 pipeline/judge.py --trial mark_2026-09-22 --calibrate --limit 5
  python3 pipeline/judge.py --trial mark_2026-09-22 --calibrate --score
  python3 pipeline/judge.py --trial mark_2026-09-22 --set resolutions
  python3 pipeline/judge.py --trial mark_2026-09-22 --only tate-conjecture
  python3 pipeline/judge.py --trial mark_2026-09-22 --check          # rebuild copies, run nothing
"""
import argparse, collections, concurrent.futures, copy, datetime, json, os, subprocess, sys, threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUSES = ('resolved', 'claimed', 'partial', 'progress', 'open_stale', 'open')
AI_ROLES = ('generated', 'assisted', 'incident', 'none')
DIRECTIONS = ('refuted', 'confirmed', 'mixed', None)
SETS = {
    'resolutions': ('resolved', 'claimed'),
    'partial': ('partial',),
    'progress': ('progress',),
    'moved': ('resolved', 'claimed', 'partial', 'progress'),
    'open': ('open', 'open_stale'),
    'all': STATUSES,
}
# Fields a verdict may change. Everything else in the copy is the original, byte for byte in value.
CHANGEABLE = ('status', 'ai_role', 'resolution_direction', 'no_change_found', 'event',
              'credited_humans', 'status_sources', 'counterexample.is_counterexample', 'ai.basis_quote')

ap = argparse.ArgumentParser()
ap.add_argument('--trial', required=True, metavar='NAME')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--set', choices=SETS, default='moved', help='which records to judge, by current status')
ap.add_argument('--calibrate', action='store_true', help='judge the human-corrected records as they were before correction')
ap.add_argument('--score', action='store_true', help='compare calibration verdicts with the human corrections')
ap.add_argument('--parallel', type=int, default=8)
ap.add_argument('--model', default='opus')
ap.add_argument('--effort', default='low', help='pinned so the run does not inherit the shell')
ap.add_argument('--limit', type=int, help='run only the first N outstanding records')
ap.add_argument('--only', nargs='+', metavar='KEY')
ap.add_argument('--check', action='store_true', help='rebuild copies from existing verdicts and validate, run nothing')
args = ap.parse_args()

TRIAL = os.path.join(ROOT, 'deepdive', args.trial)
RECORDS = os.path.join(TRIAL, 'out')
BASE = os.path.join(TRIAL, 'judged-calibration' if args.calibrate else 'judged')
VERDICTS, COPIES, LOGS = (os.path.join(BASE, d) for d in ('verdicts', 'out', 'logs'))
TODAY = datetime.date.today().isoformat()
BY = f'judging pass (JUDGE.md), {args.model}; not the researching agent and not a human reviewer'


def problems():
    rows = parse_problem_keys(os.path.join(ROOT, 'problem_keys.md'), args.revision)
    return {r['key']: r for r in rows if not r['is_grouping']}


def changed_by_hand(r):
    return any(c.get('from') != c.get('to') for c in r.get('corrections') or [])


def originals():
    """The records to judge, as the judge should see them.

    Calibration: the committed version in git, from before any hand correction, for every record a
    human has since changed. Otherwise: the current record, corrections and all, which JUDGE.md
    tells the judge to weigh as someone else's argument.
    """
    out = {}
    for f in sorted(os.listdir(RECORDS)):
        if not f.endswith('.json'):
            continue
        key, r = f[:-5], json.load(open(os.path.join(RECORDS, f), encoding='utf-8'))
        if args.calibrate:
            if not changed_by_hand(r):
                continue
            rel = os.path.relpath(os.path.join(RECORDS, f), ROOT)
            git = subprocess.run(['git', 'show', f'HEAD:{rel}'], cwd=ROOT, capture_output=True, text=True)
            if git.returncode:
                print(f'  {key}: no committed version, skipped from calibration')
                continue
            r = json.loads(git.stdout)
            r.pop('corrections', None)
        elif r.get('status') not in SETS[args.set]:
            continue
        out[key] = r
    return out


def verdict_path(key):
    return os.path.join(VERDICTS, key + '.json')


def done(key):
    p = verdict_path(key)
    return os.path.exists(p) and os.path.getsize(p) > 0


def prompt(p, r):
    lines = ['Judge this one research record, following JUDGE.md.', '',
             f"- **key**: `{p['key']}`",
             f"- **bullet**: {p['statement']}",
             f"- **field**: {p['field']}"]
    if p['parent']:
        lines.append(f"- **parent**: sub of `{p['parent']}` — {p['parent_statement']}")
    lines += ['', f'Today is {TODAY}. The record:', '', '```json',
              json.dumps(r, indent=1, ensure_ascii=False), '```', '',
              'Return a VERDICT, not a copy of the record: this harness builds the corrected copy '
              'itself from your verdict, so do not retype the record. The verdict is one JSON object:',
              '',
              '```jsonc',
              '{',
              f'  "key": "{p["key"]}",',
              '  "judgement": { ... },            // exactly as JUDGE.md §7 specifies',
              '  "changes": { "status": "partial" },  // new values, only for fields you change;',
              f'                                   // allowed keys: {", ".join(CHANGEABLE)}',
              '  "outcome_prefix": null,          // one sentence on the new event, only if `event` changes',
              '  "corrections": [                 // one per changed field, plus retentions with doubt',
              '    { "field": "status", "from": "claimed", "to": "partial", "why": "F1: …" }',
              '  ]',
              '}',
              '```', '',
              f'Write the verdict to `{os.path.relpath(verdict_path(p["key"]), ROOT)}` and write no other '
              'file anywhere.']
    return '\n'.join(lines)


def environment():
    """The inherited environment minus anything that would bill an API key or leak this session.

    This pass must never use an API key. Beyond stripping the variables, it refuses to start if the
    project's own Claude Code settings could supply one (an apiKeyHelper or an env block).
    """
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


def get(r, path):
    for part in path.split('.'):
        r = (r or {}).get(part)
    return r


def put(r, path, value):
    *head, last = path.split('.')
    for part in head:
        if not isinstance(r.get(part), dict):
            r[part] = {}
        r = r[part]
    r[last] = value


def build(key, original, v):
    """The corrected copy: the original plus the verdict's changes and corrections. Returns problems."""
    bad, c = [], copy.deepcopy(original)
    changes = v.get('changes') or {}
    for field, value in changes.items():
        if field not in CHANGEABLE:
            bad.append(f'change to {field!r} is not allowed')
            continue
        if field == 'ai.basis_quote' and not value and get(original, field):
            bad.append('ai.basis_quote blanked — evidence may be replaced, never deleted; kept the original')
            continue
        put(c, field, value)
    if 'event' in changes:
        if v.get('outcome_prefix'):
            c['outcome'] = (f"{v['outcome_prefix'].strip()} [Judged {TODAY}; the researcher's original "
                            f"outcome follows.] {original.get('outcome') or ''}").strip()
        else:
            bad.append('event changed without an outcome_prefix')
    entries = v.get('corrections') or []
    for field in changes:
        if not any(e.get('field') == field and e.get('from') != e.get('to') for e in entries):
            bad.append(f'{field} changed with no correction entry')
    for e in entries:
        if e.get('from') != e.get('to') and e.get('field') not in changes:
            bad.append(f'correction for {e.get("field")} but the field was not changed')
    c['corrections'] = (c.get('corrections') or []) + [
        dict(date=TODAY, by=BY, field=e.get('field'), **{'from': e.get('from'), 'to': e.get('to')}, why=e.get('why'))
        for e in entries]
    c['judgement'] = v.get('judgement') or {}
    bad += validate(c)
    c['judge_problems'] = bad          # merge_research.py uses a copy only when this is empty
    return c, bad


def validate(c):
    bad = []
    st, ai, d = c.get('status'), c.get('ai_role'), c.get('resolution_direction')
    if st not in STATUSES:
        bad.append(f'status {st!r}')
    if ai not in AI_ROLES:
        bad.append(f'ai_role {ai!r}')
    if d not in DIRECTIONS:
        bad.append(f'resolution_direction {d!r}')
    if st in ('resolved', 'claimed', 'partial') and not d:
        bad.append(f'{st} with no direction')
    if st in ('progress', 'open', 'open_stale') and d:
        bad.append(f'{st} with direction {d}')
    if ai not in ('none', None) and not get(c, 'ai.basis_quote'):
        bad.append(f'ai_role {ai} with no basis_quote')
    if get(c, 'counterexample.is_counterexample') and d == 'confirmed':
        bad.append('counterexample coded confirmed')
    derived = (c.get('judgement') or {}).get('derived') or {}
    for f in ('status', 'ai_role', 'resolution_direction'):
        if f in derived and derived[f] != c.get(f):
            bad.append(f'{f} is {c.get(f)!r} but the judgement derived {derived[f]!r}')
    return bad


def write_copies(keys):
    """(Re)build every copy with a verdict on disk, and report what failed validation."""
    report, changed = [], collections.Counter()
    for key in keys:
        if not done(key):
            continue
        try:
            v = json.load(open(verdict_path(key), encoding='utf-8'))
        except Exception as e:
            report.append(f'{key}: unreadable verdict ({e})')
            continue
        c, bad = build(key, ORIG[key], v)
        json.dump(c, open(os.path.join(COPIES, key + '.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        for f in (v.get('changes') or {}):
            changed[f] += 1
        report += [f'{key}: {b}' for b in bad]
    n = sum(1 for k in keys if done(k))
    print(f'\n{n} verdicts of {len(keys)} records -> {os.path.relpath(COPIES, ROOT)}')
    print('  fields changed: ' + ('  '.join(f'{f}={k}' for f, k in changed.most_common()) or 'none'))
    for line in report:
        print('  ' + line)
    return report


def score(keys):
    """Calibration: the judge's codes against the human-corrected codes now in out/."""
    fields = ('status', 'ai_role', 'resolution_direction')
    agree, rows = collections.Counter(), []
    judged = [k for k in keys if os.path.exists(os.path.join(COPIES, k + '.json'))]
    for key in judged:
        human = json.load(open(os.path.join(RECORDS, key + '.json'), encoding='utf-8'))
        judge = json.load(open(os.path.join(COPIES, key + '.json'), encoding='utf-8'))
        before = ORIG[key]
        diff = []
        for f in fields:
            if judge.get(f) == human.get(f):
                agree[f] += 1
            else:
                diff.append(f'{f}: was {before.get(f)!r}, human {human.get(f)!r}, judge {judge.get(f)!r}')
        if diff:
            rows.append((key, diff))
    n = len(judged)
    if not n:
        print('nothing judged yet')
        return
    print(f'\ncalibration: {n} records judged')
    for f in fields:
        print(f'  {f:22} {agree[f]}/{n} agree with the human call ({100 * agree[f] / n:.0f}%)')
    full = n - len(rows)
    print(f'  all three agree        {full}/{n} ({100 * full / n:.0f}%)')
    for key, diff in rows:
        print(f'\n  {key}')
        for d in diff:
            print(f'    {d}')


# Ctrl-C has to stop the run: STOP makes each queued worker refuse to start, CHILDREN lets us end
# the agents already running. Same arrangement as deep_dive.py.
STOP = threading.Event()
CHILDREN, CHILDREN_LOCK = set(), threading.Lock()


def run_one(key):
    if STOP.is_set():
        return key, None
    log = open(os.path.join(LOGS, key + '.log'), 'w')
    proc = subprocess.Popen(['claude', '-p', prompt(ALL[key], ORIG[key]),
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
    return key, done(key)


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


INSTRUCTIONS = open(os.path.join(ROOT, 'JUDGE.md'), encoding='utf-8').read()
ALL = problems()
ORIG = {k: r for k, r in originals().items() if k in ALL}
for d in (VERDICTS, COPIES, LOGS):
    os.makedirs(d, exist_ok=True)
keys = sorted(ORIG)
if args.only:
    if bad := set(args.only) - set(keys):
        sys.exit('not in this set: ' + ', '.join(sorted(bad)))
    keys = [k for k in keys if k in args.only]

if args.score:
    write_copies(keys)
    score(keys)
    sys.exit(0)

if not args.check:
    ENV = environment()
    todo = [k for k in keys if not done(k)] if not args.only else keys
    if args.limit:
        todo = todo[:args.limit]
    label = 'calibration (pre-correction versions)' if args.calibrate else f'set {args.set}'
    print(f'{len(keys)} records in {label}; {len(todo)} to judge now, {args.parallel} at a time, '
          f'model {args.model}, effort {args.effort}', flush=True)
    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (key, ok) in enumerate(pool.map(run_one, todo), 1):
            if ok is not None:
                print(f'{i:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  {key}', flush=True)
    except KeyboardInterrupt:
        print('\ninterrupted — stopping agents in flight; rerun the same command to resume')
        stop_everything()
        pool.shutdown(wait=True, cancel_futures=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)

sys.exit(1 if write_copies(keys) else 0)
