"""Add the OpenAI-stage events to the research records, as a second set of records to judge.

Step 4 of the OpenAI stage, and the last. Mechanical: no agent.

For every problem it writes deepdive/combined/<key>.json: the research record with that problem's
OpenAI events appended. Nothing is removed. Where a research agent had already recorded an OpenAI
manuscript, that event stays alongside the one this stage wrote from reading the manuscript, and
the judge answers both. The research records in deepdive/out/ are never touched, so the dataset
can always be built both ways, research alone or research plus the repository, and compared.

Only what changed is judged again. A problem with no OpenAI events has a combined record identical
to its research record, so its verdict is copied into deepdive/judged-combined/verdicts/ and
judge.py --records combined skips it. A problem that gained events is judged afresh.

  python3 pipeline/stage_3_check_the_openai_repository/combine.py --version will-2026-10-10-haiku
  python3 pipeline/stage_4_judge_the_records/judge.py --version will-2026-10-10-haiku --records combined
"""
import argparse, copy, json, os, shutil, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME')
args = ap.parse_args()
STARTED = manifest.now()

DATA = os.path.join(ROOT, 'data', args.version)
RUN = os.path.join(DATA, 'deepdive')
RESEARCH, COMBINED = os.path.join(RUN, 'out'), os.path.join(RUN, 'combined')
OLD_VERDICTS = os.path.join(RUN, 'judged', 'verdicts')
NEW_VERDICTS = os.path.join(RUN, 'judged-combined', 'verdicts')
EVENTS = os.path.join(DATA, 'openai', 'events.json')
if not os.path.exists(EVENTS):
    sys.exit(f'no {os.path.relpath(EVENTS, ROOT)} — run events.py first')
stage = json.load(open(EVENTS, encoding='utf-8'))

os.makedirs(COMBINED, exist_ok=True)
os.makedirs(NEW_VERDICTS, exist_ok=True)
changed, unchanged = [], 0

for f in sorted(os.listdir(RESEARCH)):
    if not f.endswith('.json'):
        continue
    key = f[:-5]
    r = json.load(open(os.path.join(RESEARCH, f), encoding='utf-8'))
    added = stage['events'].get(key, [])

    c = copy.deepcopy(r)
    c['events'] = list(r.get('events') or []) + [copy.deepcopy(e) for e in added]
    # Ids are unique within a record (DEEP_DIVE §7); stop rather than let a collision through.
    ids = [e.get('id') for e in c['events']]
    if len(ids) != len(set(ids)):
        sys.exit(f'{key}: duplicate event ids after combining: {ids}')
    if added:
        c['nothing_found'] = False                       # a record with events has found something
    c['combined'] = dict(openai_events_added=[e['id'] for e in added],
                         repository_commit=stage['index_commit'])
    json.dump(c, open(os.path.join(COMBINED, f), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

    if not added and os.path.exists(os.path.join(OLD_VERDICTS, f)):
        # Same events as the research record, so its verdict answers this one exactly: keep it.
        shutil.copyfile(os.path.join(OLD_VERDICTS, f), os.path.join(NEW_VERDICTS, f))
        unchanged += 1
    else:
        # Gained events: a verdict carried over from an earlier combine is stale, so remove it and
        # let the judge answer the new record.
        stale = os.path.join(NEW_VERDICTS, f)
        if os.path.exists(stale):
            os.remove(stale)
        changed.append(key)

n_added = sum(len(v) for v in stage['events'].values())
print(f'{unchanged + len(changed)} records combined -> {os.path.relpath(COMBINED, ROOT)}')
print(f'  {len(changed)} gained OpenAI-stage events ({n_added} in all) and will be judged; '
      f'{unchanged} unchanged, verdict carried over')

manifest.record(ROOT, args.version, 'openai', os.path.abspath(__file__), started=STARTED,
                counts=dict(records=unchanged + len(changed), changed=len(changed),
                            unchanged=unchanged, events_added=n_added),
                extra=dict(step='combine', index_commit=stage['index_commit'], changed=changed))
