"""Find the public release date of each AI system the research credits.

One headless claude call per model, resumable, in parallel. Reads the canonical model list out of
data/<VERSION>/research.json (only models actually credited on a problem) and writes one record
per model into data/<VERSION>/release_dates/<slug>.json, collected into release_dates.json.

Dates are load-bearing: this corpus contains results that PREDATE their model's public release,
which is a finding about pre-release and internal runs. A date wrong by a month silently turns
that into an ordinary post-release use, so the prompt refuses an unsourced date and the validator
drops any record without a quote and a URL.

  python3 pipeline/stage_6_merge_and_date_the_models/release_dates.py               # all outstanding, 4 at a time
  python3 pipeline/stage_6_merge_and_date_the_models/release_dates.py --only "GPT-6 Astra"
  python3 pipeline/stage_6_merge_and_date_the_models/release_dates.py --check       # validate and collect, run nothing
"""
import argparse, collections, concurrent.futures, json, os, re, subprocess, sys, threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import limits, manifest
ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version to work in: data/<NAME>/ — e.g. mark_2026-09-22')
ap.add_argument('--parallel', type=int, default=4)
ap.add_argument('--model', default='claude-haiku-4-5-20251001',
                help='exact model id, never an alias: an alias resolves to a different model over time, and a trial that records one cannot be read back')
ap.add_argument('--effort', default='low', help='pinned so the run does not inherit the shell')
ap.add_argument('--subscription', action='store_true',
                help='bill the Claude Code subscription instead of the API key in .secrets.json')
ap.add_argument('--only', nargs='+', metavar='MODEL', help='run only these canonical model names')
ap.add_argument('--check', action='store_true', help='validate and collect, run nothing')
args = ap.parse_args()
VERSION = args.version

DATA = os.path.join(ROOT, 'data', VERSION)
OUT = os.path.join(DATA, 'release_dates')
LOGS = os.path.join(OUT, 'logs')
BASES = ('sourced', 'tier', 'none_exists', 'unresearched')

# ----------------------------------------------------------------------------------------------
# The prompt. One model per run; everything the agent is told is here.
# ----------------------------------------------------------------------------------------------

SYSTEM = """\
You are establishing one fact: the date an AI system was first made publicly available.

## What counts as the release date

The day the system first became available to the public. Prefer, in order: the lab's own release
post or changelog, its model or system card, the system's Wikipedia article, a dated report from a
specialist outlet.

Three distinctions decide most cases:

- **Preview versus general availability.** Where a limited preview preceded a general release,
  record the general release in `release` and the preview in `preview_date`. Where a preview or
  waitlist is the only availability ever offered, record that date and say so in `note`.
- **A tier is not a model.** "Pro", "Ultra", "Extended" and the like are usually reasoning tiers of
  a base model, and usually no source dates them separately. When you cannot find a date for the
  tier itself, set `release_basis` to "tier", name the base model in `base_model`, and leave
  `release` null. Do not copy the base model's date into `release`.
- **Some systems have no release date.** An internal or unreleased build, a research prototype, an
  agent harness or orchestration system, a training algorithm, or a product line rather than one
  shipped model. That is `release_basis` "none_exists" — a real answer. Say in `note` what the
  thing is.

## Sourcing

No date without a source you opened: quote the sentence stating it and give the URL. If all you can
find is someone mentioning that they used the system on some date, that tells you it existed by
then, not when it shipped — that is "unresearched" with `release` null, not a guess.

## What to return

One JSON object, written to the path the prompt gives you, and nothing else.

```jsonc
{
  "model": "GPT-6 Astra",             // exactly as given
  "release": "2026-09-03",            // YYYY-MM-DD, or YYYY-MM if the day is unsourced, else null
  "release_basis": "sourced",         // sourced | tier | none_exists | unresearched
  "quote": "OpenAI released GPT-6 Astra on September 3, 2026.",   // verbatim; null if there is no date
  "url": "https://...",               // the page the quote is on
  "base_model": null,                 // for a tier: the base model whose date it inherits
  "preview_date": null,               // where a limited preview preceded general availability
  "kind_note": "shipped model",       // one line: what this system is
  "note": "",                         // anything else a reader needs, including what you could not settle
  "queries": ["..."],                 // every search you ran, verbatim
  "checked_on": "YYYY-MM-DD"
}
```

Two to four searches. Stop when you have a sourced date or have established there is none."""


def prompt(model, meta, out_path):
    lab = meta.get('lab') or 'unknown'
    kind = meta.get('kind') or 'unknown'
    return f"""Find the public release date of this AI system.

- **system**: {model}
- **lab**: {lab}
- **kind**: {kind}

The lab and kind are notes to help you find the right system; both may be wrong. Correct them in
`note` if what you find disagrees.

Write the record to `{out_path}` and nothing else."""


# ----------------------------------------------------------------------------------------------


slug = lambda m: re.sub(r'[^A-Za-z0-9]+', '-', m).strip('-').lower()
record = lambda m: os.path.relpath(os.path.join(OUT, slug(m) + '.json'), ROOT)


def done(m):
    p = os.path.join(OUT, slug(m) + '.json')
    return os.path.exists(p) and os.path.getsize(p) > 0


def models():
    """The canonical models research.json credits, with their lab, kind and problem count."""
    path = os.path.join(DATA, 'research.json')
    if not os.path.exists(path):
        sys.exit('no research.json — run pipeline/stage_6_merge_and_date_the_models/merge_research.py first')
    r = json.load(open(path, encoding='utf-8'))
    n = collections.Counter(m for v in list(r['by_statement'].values()) + list(r['by_name'].values())
                            for m in v['ai_models'])
    return {m: dict(v, n_problems=n[m]) for m, v in r['models'].items()}


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
LIMITED = {}                                           # model -> the usage-limit message that stopped it
CHILDREN, LOCK = set(), threading.Lock()


def run_one(job):
    m, meta = job
    if STOP.is_set():
        return m, None
    log_path = os.path.join(LOGS, slug(m) + '.log')
    log = open(log_path, 'a')                          # appended, so a retry keeps the last failure
    log.write(f'\n===== attempt started {manifest.now()} =====\n')
    log.flush()
    proc = subprocess.Popen(['claude', '-p', prompt(m, meta, record(m)),
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
    ok = done(m)
    if not ok and (msg := limits.limit_message(log_path)):
        LIMITED[m] = msg
        STOP.set()                                     # launch nothing more; it would fail the same way
    return m, ok


def check(all_models):
    records, bad = {}, []
    for m in all_models:
        path = os.path.join(OUT, slug(m) + '.json')
        if not done(m):
            bad.append(f'{m}: no record')
            continue
        try:
            r = json.load(open(path, encoding='utf-8'))
        except Exception as e:
            bad.append(f'{m}: unreadable ({e})')
            continue
        basis = r.get('release_basis')
        if basis not in BASES:
            bad.append(f'{m}: release_basis {basis!r}')
        if basis == 'sourced':
            if not r.get('release'):
                bad.append(f'{m}: sourced with no release date')
            if not (r.get('quote') and r.get('url')):
                bad.append(f'{m}: sourced with no quote and URL — a date with no source is a guess')
            if r.get('release') and not re.fullmatch(r'\d{4}-\d{2}(-\d{2})?', str(r['release'])):
                bad.append(f'{m}: release {r["release"]!r} is not YYYY-MM-DD or YYYY-MM')
        if basis == 'tier' and not r.get('base_model'):
            bad.append(f'{m}: tier with no base_model')
        if basis != 'sourced' and r.get('release'):
            bad.append(f'{m}: {basis} but carries a release date')
        if not r.get('queries'):
            bad.append(f'{m}: no queries recorded')
        records[m] = r
    counts = collections.Counter(r.get('release_basis') for r in records.values())
    print(f'\n{len(records)} of {len(all_models)} models  ' +
          '  '.join(f'{b}={counts[b]}' for b in BASES if counts[b]))
    for b in bad:
        print('  ' + b)
    json.dump(records, open(os.path.join(DATA, 'release_dates.json'), 'w', encoding='utf-8'),
              indent=1, ensure_ascii=False)
    print('-> ' + os.path.relpath(os.path.join(DATA, 'release_dates.json'), ROOT))
    return bad


ALL = models()
os.makedirs(LOGS, exist_ok=True)

if not args.check:
    ENV = environment()
    todo = [m for m in sorted(ALL) if not done(m)]
    if args.only:
        todo = [m for m in args.only if m in ALL]
        if miss := set(args.only) - set(todo):
            sys.exit('no such model: ' + ', '.join(sorted(miss)))
    print(f'{len(todo)} of {len(ALL)} models to run, {args.parallel} at a time, model {args.model}')
    STARTED = manifest.now()
    pool = concurrent.futures.ThreadPoolExecutor(args.parallel)
    try:
        for i, (m, ok) in enumerate(pool.map(run_one, [(m, ALL[m]) for m in todo]), 1):
            if ok is not None:
                print(f'{i:3}/{len(todo)}  {"LIMIT" if m in LIMITED else "ok  " if ok else "FAIL"}  {m}', flush=True)
    except KeyboardInterrupt:
        print('\ninterrupted — rerun the same command to resume')
        STOP.set()
        with LOCK:
            procs = list(CHILDREN)
        for p in procs:
            p.terminate()
        pool.shutdown(wait=True, cancel_futures=True)
        sys.exit(130)
    finally:
        pool.shutdown(wait=True)
    if LIMITED:
        print(f'\nstopped at the usage limit ({next(iter(LIMITED.values()))}). '
              'Rerun the same command after the reset to resume.', flush=True)

if not args.check:
    # What produced these records: the exact model, the prompt's hash, the commit, the counts.
    manifest.record(ROOT, args.version, 'dates', os.path.abspath(__file__),
                    args.model, args.effort, args.parallel,
                    prompt_path=None,
                    selection=dict(only=args.only),
                    counts=dict(models=len(ALL), ran=len(todo)),
                    started=STARTED,
                    extra=dict(billing='subscription' if args.subscription else 'api_key',
                               limited=sorted(LIMITED), limit_message=next(iter(LIMITED.values()), None)))

sys.exit(1 if check(sorted(ALL)) else 0)
