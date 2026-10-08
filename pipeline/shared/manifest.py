"""What produced a trial's records: the model, the prompt, the code, and when.

A record says what was found. This says what found it. Without the model and the prompt that
produced a set of records, the set cannot be read a year later, and cannot be compared with any
other set — which is the whole point of fixing the denominator.

Both prompts have been rewritten repeatedly, so the prompt's hash is as load-bearing as the model
name: two runs of `deep_dive.py` on the same model against different DEEP_DIVE.md are different
instruments. The git commit is recorded too, but the hash is what survives an uncommitted edit.

One file per trial per stage, at data/<version>/manifests/<stage>.json, holding a list: an agent
stage is resumable, so a stage usually runs several times and every run is appended. Nothing is
ever overwritten.
"""
import datetime, hashlib, json, os, subprocess


def _sha256(path):
    try:
        return hashlib.sha256(open(path, 'rb').read()).hexdigest()[:16]
    except OSError:
        return None


def _git(root, *args):
    try:
        r = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def record(root, version, stage, script, model=None, effort=None, parallel=None,
           prompt_path=None, selection=None, counts=None, started=None, extra=None):
    """Append one run to data/<version>/manifests/<stage>.json and return what was written.

    `script` and `prompt_path` are absolute. `started` is an ISO string from before the run; the
    finish time is taken here. `model`, `effort` and `parallel` are None for the mechanical stages,
    which call no model — what identifies those runs is the script hash and the commit. `extra`
    carries whatever else pins a stage down, such as the revision id a fetch pulled.

    Never raises: a manifest that fails to write must not lose a run that cost money, so problems
    are reported and the run stands.
    """
    now = datetime.datetime.now().astimezone()
    entry = dict(
        stage=stage,
        version=version,
        model=model,                      # the exact id passed to the CLI, never an alias
        effort=effort,
        parallel=parallel,
        started=started,
        finished=now.isoformat(timespec='seconds'),
        script=dict(path=os.path.relpath(script, root), sha256=_sha256(script)),
        prompt=(dict(path=os.path.relpath(prompt_path, root), sha256=_sha256(prompt_path))
                if prompt_path else None),
        git=dict(commit=_git(root, 'rev-parse', 'HEAD'),
                 # Scoped to pipeline/, because a run writes into data/ and that would otherwise
                 # mark every script after the first one dirty. What matters here is whether the
                 # commit describes the code that ran; the outputs changing is the point.
                 # True means it does not, and the hashes above are what pin the run down.
                 dirty=bool(_git(root, 'status', '--porcelain', '--', 'pipeline'))),
        selection=selection or {},
        counts=counts or {},
        **(extra or {}),
    )
    try:
        path = os.path.join(root, 'data', version, 'manifests', stage + '.json')
        os.makedirs(os.path.dirname(path), exist_ok=True)
        runs = json.load(open(path, encoding='utf-8')) if os.path.exists(path) else []
        if not isinstance(runs, list):
            runs = [runs]
        runs.append(entry)
        json.dump(runs, open(path, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
        print(f'manifest -> {os.path.relpath(path, root)} (run {len(runs)})')
    except Exception as e:                # noqa: BLE001 — never lose a run over bookkeeping
        print(f'WARNING: could not write the manifest ({e}). This run is unrecorded:')
        print(json.dumps(entry, indent=1, ensure_ascii=False))
    return entry


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
