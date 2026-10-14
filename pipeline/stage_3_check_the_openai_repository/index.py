"""Index the openai/math repository: every manuscript, its family, when it went public, its Lean status.

The repository is the largest single source of AI claims on the list, and a research agent finds
its manuscripts only some of the time. This stage reads it directly instead, from a local clone
pinned by commit, so that every later step works from the same fixed text.

Mechanical: no agent, no network. Everything here is read off the clone:

  CONTENTS.md               the 372 families, their summaries, and each manuscript's abstract
  preprints/<folder>/       one folder per manuscript; its README says whether it was withdrawn
  lean/formalization.yaml   the formalised main results and their Comparator configs
  lean/docs/<family>.md     for each formalised family, the papers it covers and the scope of what
                            the Lean actually proves, which can be narrower than the paper's claim
  README.md                 the AI statement and its named exceptions, quoted verbatim
  git history               when each folder first appeared publicly

A manuscript's date is the first public commit containing it. The date in a folder's name is when
it was written, and DEEP_DIVE.md §5.1 dates an event by its first public written argument.

Clone once, outside version control (sources/ is gitignored), with its history but no old blobs:

  git clone --filter=blob:none https://github.com/openai/math sources/openai-math

  python3 pipeline/stage_3_check_the_openai_repository/index.py --version will-2026-10-10-haiku
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'shared'))
import manifest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_URL = 'https://github.com/openai/math'

ap = argparse.ArgumentParser()
ap.add_argument('--version', required=True, metavar='NAME',
                help='the dataset version this index belongs to: data/<NAME>/openai/')
ap.add_argument('--source', default=os.path.join(ROOT, 'sources', 'openai-math'),
                help='the local clone of openai/math')
args = ap.parse_args()
STARTED = manifest.now()

DATA = os.path.join(ROOT, 'data', args.version)
OUT = os.path.join(DATA, 'openai')
SRC = os.path.abspath(args.source)
if not os.path.isdir(DATA):
    sys.exit(f'no data/{args.version}/ — run the fetch stage first, or check the name')
if not os.path.isdir(os.path.join(SRC, 'preprints')):
    sys.exit(f'no clone at {os.path.relpath(SRC, ROOT)} — see the docstring for the clone command')


def git(*a):
    return subprocess.run(['git', *a], cwd=SRC, capture_output=True, text=True, check=True).stdout


# The index is only reproducible against a fixed text, so refuse a clone with local edits.
if git('status', '--porcelain').strip():
    sys.exit(f'{os.path.relpath(SRC, ROOT)} has local changes; the index must describe a pinned commit')
COMMIT = git('rev-parse', 'HEAD').strip()
COMMIT_DATE = git('log', '-1', '--format=%cI').strip()


def read(rel):
    return open(os.path.join(SRC, rel), encoding='utf-8').read()


def plain(s):
    """CONTENTS.md prose with the HTML stripped; inline LaTeX is kept as written."""
    s = re.sub(r'<sub>(.*?)</sub>', r'_\1', s)
    s = re.sub(r'<sup>(.*?)</sup>', r'^\1', s)
    s = re.sub(r'<[^>]+>', '', s).replace('&emsp;', '').replace('&nbsp;', ' ')
    return re.sub(r'\s+', ' ', s).strip()


# ---- when each folder first went public: the earliest commit whose tree contains it
public = {}
for line in git('log', '--reverse', '--format=%H %cI').splitlines():
    sha, when = line.split()
    for name in git('ls-tree', '--name-only', sha, 'preprints/').split():
        public.setdefault(name.split('/', 1)[-1], dict(date=when[:10], commit=sha))

# ---- families and manuscripts, from CONTENTS.md
contents = read('CONTENTS.md')
families, listed = [], {}
for m in re.finditer(r'\*\*(\d{3})\. (.+?)\*\*(.*?)(?=\n\*\*\d{3}\. |\Z)', contents, re.S):
    num, title, body = m.group(1), plain(m.group(2)), m.group(3)
    papers = []
    for p in re.finditer(r'\[([^\]]+)\]\(preprints/([^/]+)/([^)]+)\)\s*(.*?)</td>', body, re.S):
        folder = p.group(2)
        papers.append(folder)
        listed[folder] = dict(title=plain(p.group(1)), family=num, file=p.group(3), abstract=plain(p.group(4)))
    families.append(dict(num=num, title=title.rstrip('.'), summary=plain(body.split('</td>')[0]),
                         manuscripts=papers))

# ---- Lean: the per-family scope documents, and the Comparator configs they link
main_results = {}
for c, d, f in re.findall(r'comparator_config: (\S+)\n\s+declaration: (\S+)\n\s+file: (\S+)',
                          read('lean/formalization.yaml')):
    main_results[c] = dict(declaration=d, file=f)

lean_by_family, lean_by_folder = {}, {}
for doc in sorted(os.listdir(os.path.join(SRC, 'lean', 'docs'))):
    if not doc.endswith('.md'):
        continue
    text = read(f'lean/docs/{doc}')
    num = doc[:-3]
    covers = sorted(set(re.findall(r'\.\./\.\./preprints/([^/)]+)/', text)))
    scope = text.split('## Scope', 1)[1].split('\n## ', 1)[0].strip() if '## Scope' in text else None
    results = []
    for label, lean_file in re.findall(r'\|\s*([^|\n]+?)\s*\|\s*\[[^\]]+\]\(\.\./(ComparatorChallenges/[^)]+)\.lean\)', text):
        cfg = lean_file + '.json'
        conf = json.loads(read(f'lean/{cfg}')) if os.path.exists(os.path.join(SRC, 'lean', cfg)) else {}
        results.append(dict(result=label, comparator_config=cfg,
                            theorems=conf.get('theorem_names') or [],
                            permitted_axioms=conf.get('permitted_axioms') or [],
                            **main_results.get(cfg, {})))
    lean_by_family[num] = dict(doc=f'lean/docs/{doc}', scope=scope, covers=covers, results=results)
    for folder in covers:
        lean_by_folder.setdefault(folder, []).append(num)

# ---- every manuscript folder, listed in CONTENTS.md or not
manuscripts = []
for folder in sorted(os.listdir(os.path.join(SRC, 'preprints'))):
    path = os.path.join(SRC, 'preprints', folder)
    if not os.path.isdir(path):
        continue
    readme = read(f'preprints/{folder}/README.md') if os.path.exists(os.path.join(path, 'README.md')) else ''
    withdrawn = re.search(r'Withdrawn on ([A-Z][a-z]+ \d{1,2}, \d{4})', readme)
    written = re.search(r'([A-Z][a-z]+-\d{1,2}-\d{4})$', folder)
    entry = listed.get(folder, {})
    pdf = entry.get('file') or next((f for f in sorted(os.listdir(path)) if f.endswith('.pdf')), None)
    manuscripts.append(dict(
        folder=folder,
        title=entry.get('title') or (re.search(r'^# \[(.+?)\]', readme, re.M) or [None, folder])[1],
        family=entry.get('family'),
        listed_in_contents=folder in listed,
        abstract=entry.get('abstract'),
        written=written.group(1).replace('-', ' ', 1).replace('-', ', ') if written else None,
        public=public.get(folder, {}).get('date'),
        public_commit=public.get(folder, {}).get('commit'),
        withdrawn=withdrawn.group(1) if withdrawn else None,
        pdf=f'preprints/{folder}/{pdf}' if pdf else None,
        url=f'{REPO_URL}/blob/{COMMIT}/preprints/{folder}/{pdf}' if pdf else f'{REPO_URL}/tree/{COMMIT}/preprints/{folder}',
        lean_families=lean_by_folder.get(folder, []),
    ))

# A revised manuscript keeps its old folder beside the new one, and only the new one is listed.
# Link the editions by title, so a result is dated by the first edition that carried it (§5.1).
title_key = lambda t: re.sub(r'[^a-z0-9]+', ' ', t.lower().replace('withdrawal notice:', '')).strip()
current = {title_key(m['title']): m for m in manuscripts if m['listed_in_contents']}
for m in manuscripts:
    m['superseded_by'] = None
    if not m['listed_in_contents'] and not m['withdrawn']:
        head = current.get(title_key(m['title']))
        if head:
            m['superseded_by'] = head['folder']
for m in manuscripts:
    editions = [e for e in manuscripts if e is m or e['superseded_by'] == m['folder']]
    m['editions'] = sorted(e['folder'] for e in editions if e is not m)
    m['first_public'] = min((e['public'] for e in editions if e['public']), default=None)

for f in families:
    f['lean'] = lean_by_family.get(f['num'])

# ---- the attribution, quoted verbatim: later steps cite it, they do not paraphrase it
readme = read('README.md')
quote = lambda pattern: (re.search(pattern, readme) or [None])[0]
ai = dict(
    repository=quote(r'This repository contains [^\n]*?OpenAI model\.'),
    procedure=quote(r'The vast majority of results were obtained [^\n]*?model\.'),
    exceptions=quote(r'Exceptions to this fixed procedure include [^\n]*?\.(?= |\n)'),
    human_edited=quote(r'Additionally, the writeup [^\n]*?readability\.'),
    url=f'{REPO_URL}/blob/{COMMIT}/README.md',
)
missing = [k for k, v in ai.items() if not v]
if missing:
    sys.exit(f'README.md no longer contains the expected AI statement ({", ".join(missing)}); '
             'read it and update the patterns before indexing')

index = dict(
    repository=dict(url=REPO_URL, commit=COMMIT, commit_date=COMMIT_DATE,
                    first_public=min(m['public'] for m in manuscripts if m['public'])),
    ai_statement=ai,
    families=families,
    manuscripts=manuscripts,
)
os.makedirs(OUT, exist_ok=True)
json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)

n_lean = sum(1 for m in manuscripts if m['lean_families'])
counts = dict(families=len(families), manuscripts=len(manuscripts),
              listed=sum(m['listed_in_contents'] for m in manuscripts),
              withdrawn=sum(bool(m['withdrawn']) for m in manuscripts),
              earlier_editions=sum(bool(m['superseded_by']) for m in manuscripts),
              with_lean=n_lean, lean_families=len(lean_by_family))
print(f"{counts['manuscripts']} manuscripts in {counts['families']} families "
      f"({counts['listed']} listed in CONTENTS.md, {counts['earlier_editions']} earlier editions of "
      f"revised ones, {counts['withdrawn']} withdrawn, "
      f"{n_lean} covered by a Lean scope document across {len(lean_by_family)} families)")
print(f"repository at {COMMIT[:9]} ({COMMIT_DATE}); first public {index['repository']['first_public']}")
print('-> ' + os.path.relpath(os.path.join(OUT, 'index.json'), ROOT))

manifest.record(ROOT, args.version, 'openai', os.path.abspath(__file__), counts=counts, started=STARTED,
                extra=dict(step='index', source=dict(url=REPO_URL, commit=COMMIT, commit_date=COMMIT_DATE)))
