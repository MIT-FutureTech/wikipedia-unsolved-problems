"""Run the judging pass: one headless claude call per research record, in parallel, resumable.

Each agent gets JUDGE.md as its system prompt and one deep-dive record, and writes a verdict: its
answers for every event, the event the status rests on, and the codes those answers imply. The
research record carries no codes of its own, so this pass is where a problem is first classified —
it is not correcting anyone. This script then builds the judged copy itself, lifting the resting
event's date, sources and credited people straight from the record, so nothing the agent retyped
reaches the dataset. The originals in data/<version>/deepdive/out/ are never touched.

  data/<version>/deepdive/judged/verdicts/<key>.json   the agent's verdict
  data/<version>/deepdive/judged/out/<key>.json        the judged copy
  data/<version>/deepdive/judged-calibration/...       the same, for --calibrate

Runs on the Claude Code subscription: any ANTHROPIC_API_KEY is removed from the environment, so
each call uses the logged-in account (deep_dive.py bills an API key instead).

--calibrate and --score are v1 instruments: they scored this pass against human corrections to the
codes the *research* pass used to emit. A v2 record has no codes to correct, so there is no
baseline; recalibrating would need human-written verdicts to score against.

  python3 pipeline/stage_4_judge_the_records/judge.py --version mark_2026-09-22 --limit 5
  python3 pipeline/stage_4_judge_the_records/judge.py --version mark_2026-09-22 --set events
  python3 pipeline/stage_4_judge_the_records/judge.py --version mark_2026-09-22 --only tate-conjecture
  python3 pipeline/stage_4_judge_the_records/judge.py --version mark_2026-09-22 --check          # rebuild copies, run nothing
"""
import argparse, collections, concurrent.futures, copy, datetime, json, os, subprocess, sys, threading

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import limits, manifest
from wikitext import parse_problem_keys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# The judge's own vocabularies. The research record carries no codes, so nothing here is checked
# against the record: these are the values this pass produces (JUDGE.md §2 and §3).
STATUSES = ('resolved', 'claimed', 'partial', 'progress', 'open_stale', 'open')
AI_ROLES = ('generated', 'assisted', 'none')
DIRECTIONS = ('refuted', 'confirmed', 'mixed', None)
SCOPES = ('whole', 'case', 'bound', 'instances', 'variant', 'none')
VERIFICATIONS = ('digested', 'checkable', 'unreviewed')
CREDIBILITIES = ('credible', 'doubtful', 'not_credible', 'knocked_down')
CONFIDENCE = ('high', 'medium', 'low')
OBJECT_ROLES = ('counterexample', 'witness', None)
# §3 step 1: an event answered this way never sets the status.
DISCARD_SCOPE = ('instances', 'variant', 'none')
DISCARD_CREDIBILITY = ('not_credible', 'knocked_down')
TIERS = ('progress', 'partial', 'claimed', 'resolved')      # ascending, for §3 step 3
# A record can no longer be selected by its status, because it has none. What it does have is
# events or not: `quiet` is the nothing_found set, which JUDGE.md still asks a judge to look at so
# that a broken search is not mistaken for a quiet problem.
SETS = {'all': None, 'events': True, 'quiet': False}

ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version whose records to judge — e.g. mark_2026-09-22')
ap.add_argument('--revision', default='2024-01')
ap.add_argument('--set', choices=SETS, default='all',
                help='which records to judge: all, events (at least one event), quiet (nothing_found)')
ap.add_argument('--calibrate', action='store_true', help='judge the human-corrected records as they were before correction')
ap.add_argument('--score', action='store_true', help='compare calibration verdicts with the human corrections')
ap.add_argument('--parallel', type=int, default=8)
ap.add_argument('--model', default='claude-opus-5-5',
                help='exact model id, never an alias: an alias resolves to a different model over time, and a trial that records one cannot be read back')
ap.add_argument('--effort', default='low', help='pinned so the run does not inherit the shell')
ap.add_argument('--limit', type=int, help='run only the first N outstanding records')
ap.add_argument('--only', nargs='+', metavar='KEY')
ap.add_argument('--check', action='store_true', help='rebuild copies from existing verdicts and validate, run nothing')
args = ap.parse_args()

RUN = os.path.join(ROOT, 'data', args.version, 'deepdive')
RECORDS = os.path.join(RUN, 'out')
BASE = os.path.join(RUN, 'judged-calibration' if args.calibrate else 'judged')
if not os.path.isdir(RECORDS):
    sys.exit(f'no records in data/{args.version}/deepdive/out/ — run pipeline/stage_2_research_each_problem/deep_dive.py first, '
             'or check the name against the folders under data/')
VERDICTS, COPIES, LOGS = (os.path.join(BASE, d) for d in ('verdicts', 'out', 'logs'))
TODAY = datetime.date.today().isoformat()
BY = f'judging pass (JUDGE.md), {args.model}; not the researching agent and not a human reviewer'


def problems():
    rows = parse_problem_keys(os.path.join(ROOT, 'data', args.version, 'problem_keys.md'), args.revision)
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
        elif SETS[args.set] is not None and bool(r.get('events')) != SETS[args.set]:
            continue
        out[key] = r
    return out


def verdict_path(key):
    return os.path.join(VERDICTS, key + '.json')


def done(key):
    """A verdict counts only if it parses and answers every event, so a skipped event is retried."""
    p = verdict_path(key)
    if not (os.path.exists(p) and os.path.getsize(p) > 0):
        return False
    try:
        v = json.load(open(p, encoding='utf-8'))
    except ValueError:
        return False
    want = {e.get('id') for e in (ORIG.get(key, {}).get('events') or [])}
    return want <= {e.get('id') for e in (v.get('events') or [])}


def prompt(p, r):
    lines = ['Judge this one research record, following JUDGE.md.', '',
             f"- **key**: `{p['key']}`",
             f"- **statement**: {p['statement']}",
             f"- **field**: {p['field']}"]
    if p['parent']:
        lines.append(f"- **parent**: sub of `{p['parent']}` — {p['parent_statement']}")
    lines += ['', f'Today is {TODAY}. The record:', '', '```json',
              json.dumps(r, indent=1, ensure_ascii=False), '```', '',
              'Return a VERDICT: your answers for each event, and nothing else. You assign no '
              'status and pick no winning event — the harness derives those from these rows by '
              'JUDGE.md §3. It also takes each event\'s date, sources and people from the record, '
              'so do not retype any of it. One JSON object, as JUDGE.md §5 specifies:',
              '',
              '```jsonc',
              '{',
              f'  "key": "{p["key"]}",',
              '  "events": [{                     // one row per event in the record, in its order,',
              '                                   // including ones you discard and ones before the snapshot',
              '    "id": "<the record\'s event id>",',
              '    "after_snapshot": true,        // true | false | null where the date cannot be placed (Q1)',
              f'    "scope": …,                    // {" | ".join(SCOPES)}',
              f'    "verification": …,             // {" | ".join(VERIFICATIONS)}',
              f'    "credibility": …,              // {" | ".join(CREDIBILITIES)}',
              '    "credibility_reason": null,    // required unless credible',
              f'    "ai_role": …,                  // {" | ".join(AI_ROLES)} — for THIS event, from its own quote',
              '    "ai_basis": null,              // the quote you relied on, where not none',
              '    "ai_systems_credited": [],     // names from this event\'s ai.systems, exactly as recorded',
              f'    "direction": …,                // {" | ".join(str(d) for d in DIRECTIONS)}',
              f'    "object_role": null            // {" | ".join(str(o) for o in OBJECT_ROLES)}',
              '  }],',
              '  "why": "…",',
              '  "doubts": null,',
              '  "insufficient_evidence": false,',
              f'  "confidence": "high"             // {" | ".join(CONFIDENCE)}',
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


AI_STRENGTH = {'none': 0, 'assisted': 1, 'generated': 2}


def tier_of(row):
    """JUDGE.md §3 steps 1-2: the tier an answered event earns, or None where step 1 discards it."""
    if row.get('scope') in DISCARD_SCOPE or row.get('credibility') in DISCARD_CREDIBILITY:
        return None
    scope, verified = row.get('scope'), row.get('verification')
    if scope == 'whole':
        return 'resolved' if verified in ('digested', 'checkable') else 'claimed'
    return {'case': 'partial', 'bound': 'progress'}.get(scope)


def derive(rows, events):
    """JUDGE.md §3, in full: the problem's codes from the judge's per-event answers.

    The judge answers six questions per event and nothing else. Everything a problem is finally
    counted as is computed here, so a change to the rules below re-derives every record from the
    verdicts already on disk, without running an agent again.
    """
    live = {r.get('id'): t for r in rows if (t := tier_of(r))}
    placed = {r.get('id'): r.get('after_snapshot') for r in rows}
    # An undatable event (after_snapshot null) is in neither set, so it can set neither status.
    after = {i: t for i, t in live.items() if placed.get(i) is True}

    if not after:                                        # step 5
        stale = any(t == 'resolved' for i, t in live.items() if placed.get(i) is False)
        return dict(status='open_stale' if stale else 'open', rests_on=None,
                    ai_role='none', ai_from=None, resolution_direction=None, object_role=None,
                    ai_systems_credited=[])

    best = max(after.values(), key=TIERS.index)          # step 3
    winners = [i for i, t in after.items() if t == best]
    # Ties break on the record's date: the first event to reach the top tier is when the problem
    # moved. Missing dates sort last so a dated event is always preferred.
    # TODO: compare by precision, not as strings. '2026-07' sorts before '2026-07-03' though it may be
    # later, and a year-precision date with a placeholder month sorts as that month. Dates that
    # cannot be ordered at their shared precision should count as a tie, not as earlier.
    rests_on = min(winners, key=lambda i: str((events.get(i) or {}).get('date') or '9999'))
    row = next(r for r in rows if r.get('id') == rests_on)
    # Step 4: AI counts if any event at the top tier was AI, whichever one step 3 rested on.
    ai_role = max((next(r for r in rows if r.get('id') == i).get('ai_role') or 'none'
                   for i in winners), key=lambda a: AI_STRENGTH.get(a, 0))
    # The AI credit comes from a top-tier event that carries it, which need not be the one the
    # status rests on; ai_from names it, so its systems and quote are looked up in the right place.
    ai_from = next((i for i in winners
                    if (next(r for r in rows if r.get('id') == i).get('ai_role') or 'none') == ai_role
                    and ai_role != 'none'), None)
    credited = (next(r for r in rows if r.get('id') == ai_from).get('ai_systems_credited') or []) if ai_from else []
    return dict(status=best, rests_on=rests_on, ai_role=ai_role, ai_from=ai_from,
                # step 6: only a settled tier carries a direction
                resolution_direction=row.get('direction') if best in ('resolved', 'claimed', 'partial') else None,
                object_role=row.get('object_role'),
                ai_systems_credited=credited)


def build(key, original, v):
    """The judged copy: the record, plus the codes §3 derives from the verdict. Returns problems.

    The judge supplies per-event answers only. The codes here are computed, and every other fact is
    lifted from the record, so nothing the judging agent retyped reaches the dataset.
    """
    bad = validate(original, v)
    c = copy.deepcopy(original)
    events = {e.get('id'): e for e in (original.get('events') or []) if e.get('id')}
    rows = v.get('events') or []

    d = derive(rows, events)
    if v.get('insufficient_evidence'):                   # F16 overrides everything
        d = dict(status='open', rests_on=None, ai_role='none', ai_from=None, resolution_direction=None,
                 object_role=None, ai_systems_credited=[])
    ev = events.get(d['rests_on']) or {}
    ai_ev = events.get(d['ai_from']) or {}               # where the AI credit came from (step 4)

    c['status'] = d['status']
    c['ai_role'] = d['ai_role']
    c['resolution_direction'] = d['resolution_direction']
    c['object_role'] = d['object_role']
    # The site and merge_research.py read the older boolean; a witness is not a counterexample.
    c['counterexample'] = {'is_counterexample': d['object_role'] == 'counterexample'}
    c['rests_on'] = d['rests_on']
    c['no_change_found'] = bool(original.get('nothing_found'))

    c['event'] = ev or None                              # singular: the shape merge_research.py reads
    c['credited_humans'] = ev.get('people') or []
    c['status_sources'] = ev.get('sources') or []
    recorded = {sy.get('name'): sy for sy in ((ai_ev.get('ai') or {}).get('systems') or [])}
    credited = [n for n in d['ai_systems_credited']]
    for n in credited:
        if n not in recorded:
            bad.append(f'{n!r} credited on {d["ai_from"]}, which does not record it')
    c['ai'] = {'systems': credited,
               'from_event': d['ai_from'],               # may differ from rests_on, by step 4
               'basis_quote': next((recorded[n].get('basis_quote') for n in credited if n in recorded), None),
               'none_found': (ev.get('ai') or {}).get('none_found'),
               'disclosed_cost': (ai_ev.get('ai') or {}).get('disclosed_cost')}
    if d['ai_role'] != 'none' and not c['ai']['basis_quote']:
        bad.append(f'derived ai_role {d["ai_role"]} with no basis_quote behind it')

    c['judgement'] = {k: v.get(k) for k in
                      ('events', 'why', 'doubts', 'insufficient_evidence', 'confidence')}
    c['judgement'].update(derived=d, date=TODAY, by=BY)
    c['judge_problems'] = bad        # merge_research.py uses a copy only when this is empty
    return c, bad


def validate(original, v):
    """The judge's answers. Nothing here checks a code: the codes are derived, not asserted."""
    bad = []
    if v.get('confidence') not in CONFIDENCE:
        bad.append(f'confidence {v.get("confidence")!r}')
    if not v.get('why'):
        bad.append('no `why`')
    rows = v.get('events') or []
    for e in rows:
        at = f'event {e.get("id")!r}'
        if e.get('scope') not in SCOPES:
            bad.append(f'{at}: scope {e.get("scope")!r}')
        if e.get('verification') not in VERIFICATIONS:
            bad.append(f'{at}: verification {e.get("verification")!r}')
        if e.get('credibility') not in CREDIBILITIES:
            bad.append(f'{at}: credibility {e.get("credibility")!r}')
        elif e.get('credibility') != 'credible' and not e.get('credibility_reason'):
            bad.append(f'{at}: {e.get("credibility")} with no credibility_reason')
        if e.get('ai_role') not in AI_ROLES:
            bad.append(f'{at}: ai_role {e.get("ai_role")!r}')
        elif e.get('ai_role') != 'none' and not e.get('ai_basis'):
            bad.append(f'{at}: ai_role {e.get("ai_role")} with no ai_basis')
        if e.get('object_role') not in OBJECT_ROLES:
            bad.append(f'{at}: object_role {e.get("object_role")!r}')
        if e.get('direction') not in DIRECTIONS:
            bad.append(f'{at}: direction {e.get("direction")!r}')
        elif e.get('object_role') == 'counterexample' and e.get('direction') == 'confirmed':
            bad.append(f'{at}: counterexample answered confirmed (F14)')
        if 'after_snapshot' not in e or not (e['after_snapshot'] is None or isinstance(e['after_snapshot'], bool)):
            bad.append(f'{at}: after_snapshot {e.get("after_snapshot")!r}')
    # Every event answered, and nothing invented.
    in_record = {e.get('id') for e in (original.get('events') or [])}
    answered = {e.get('id') for e in rows}
    for miss in sorted(x for x in in_record - answered if x):
        bad.append(f'event {miss!r} in the record has no row in the verdict')
    for extra in sorted(x for x in answered - in_record if x):
        bad.append(f'verdict answers {extra!r}, which is not an event in the record')
    return bad


def write_copies(keys):
    """(Re)build every copy with a verdict on disk, and report what failed validation."""
    report, changed = [], collections.Counter()
    for key in keys:
        # Any verdict on disk, complete or not, so an incomplete one is still built and reported.
        if not os.path.exists(verdict_path(key)):
            continue
        try:
            v = json.load(open(verdict_path(key), encoding='utf-8'))
        except Exception as e:
            report.append(f'{key}: unreadable verdict ({e})')
            continue
        c, bad = build(key, ORIG[key], v)
        json.dump(c, open(os.path.join(COPIES, key + '.json'), 'w', encoding='utf-8'), indent=2, ensure_ascii=False)
        changed[c.get('status')] += 1
        if (c.get('ai_role') or 'none') != 'none':
            changed['(AI credited)'] += 1
        report += [f'{key}: {b}' for b in bad]
    n = sum(1 for k in keys if done(k))
    print(f'\n{n} verdicts of {len(keys)} records -> {os.path.relpath(COPIES, ROOT)}')
    print('  status: ' + ('  '.join(f'{f}={k}' for f, k in changed.most_common()) or 'none'))
    for line in report:
        print('  ' + line)
    return report


def score(keys):
    """Calibration: the judge's codes against the human-corrected codes now in out/.

    Only meaningful for v1 records. It scored this pass against human corrections to codes the
    *research* pass had assigned, and the research pass no longer assigns any: a v2 record has
    nothing to correct and nothing to compare with. Recalibrating needs a set of human-written
    verdicts, which does not exist yet.
    """
    if any('status' not in (ORIG.get(k) or {}) for k in keys):
        sys.exit('--score needs records that carry their own codes, and v2 records do not. '
                 'Calibration against human corrections has no baseline here: it would need human-'
                 'written verdicts to score against, which this dataset does not have yet.')
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
LIMITED = {}                                       # key -> the usage-limit message that stopped it


def run_one(key):
    if STOP.is_set():
        return key, None
    # Appended, not overwritten: a retry must not erase why the attempt before it failed.
    log = open(os.path.join(LOGS, key + '.log'), 'a')
    log.write(f'\n===== attempt started {manifest.now()} =====\n')
    log.flush()
    proc = subprocess.Popen(['claude', '-p', prompt(ALL[key], ORIG[key]),
                             '--append-system-prompt', INSTRUCTIONS,
                             '--model', args.model,
                             '--effort', args.effort,
                             # No search: JUDGE.md forbids it, and a verdict that reached past
                             # the record could not be compared with the others or re-derived.
                             '--allowedTools', 'Write',
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
    ok = done(key)
    if not ok and (msg := limits.limit_message(os.path.join(LOGS, key + '.log'))):
        LIMITED[key] = msg
        STOP.set()                                 # launch nothing more; it would fail the same way
    return key, ok


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


INSTRUCTIONS = open(os.path.join(ROOT, 'pipeline', 'prompts', 'JUDGE.md'), encoding='utf-8').read()
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
    STARTED = manifest.now()
    failed = []

    def record_run(interrupted=False):
        # What produced these verdicts. Written on an interrupt too, so none go unaccounted for.
        manifest.record(ROOT, args.version, 'judge', os.path.abspath(__file__),
                        args.model, args.effort, args.parallel,
                        prompt_path=os.path.join(ROOT, 'pipeline', 'prompts', 'JUDGE.md'),
                        selection=dict(only=args.only, limit=args.limit, set=args.set, calibrate=args.calibrate),
                        counts=dict(records=len(keys), verdicts=sum(1 for k in keys if done(k)),
                                    ran=len(todo) - len(skipped), failed=len(failed),
                                    limited=len(LIMITED), not_started=len(skipped)),
                        started=STARTED,
                        extra=dict(failed=failed, interrupted=interrupted, limited=sorted(LIMITED),
                                   limit_message=next(iter(LIMITED.values()), None)))

    skipped = []
    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (key, ok) in enumerate(pool.map(run_one, todo), 1):
            if ok is None:
                skipped.append(key)                # never started: interrupted, or the limit was hit
            elif key in LIMITED:
                print(f'{i:4}/{len(todo)}  LIMIT {key}', flush=True)
            else:
                if not ok:
                    failed.append(key)
                print(f'{i:4}/{len(todo)}  {"ok  " if ok else "FAIL"}  {key}', flush=True)
    except KeyboardInterrupt:
        print('\ninterrupted — stopping agents in flight; rerun the same command to resume')
        stop_everything()
        pool.shutdown(wait=True, cancel_futures=True)
        record_run(interrupted=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)
    if LIMITED:
        print(f'\nstopped at the usage limit ({next(iter(LIMITED.values()))}): {len(LIMITED)} hit it, '
              f'{len(skipped)} not started. Rerun the same command after the reset to resume.', flush=True)
    record_run()

sys.exit(1 if write_copies(keys) else 0)
