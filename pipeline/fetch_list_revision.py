"""Fetch the frozen revision of the list, strip <ref>...</ref>, save page.wiki.

The frozen revision (oldid 1199136318, 26 Jan 2024) becomes data/<VERSION>/page.wiki, which is
the denominator: every problem researched downstream is a bullet in this file.

Run: python3 pipeline/fetch_list_revision.py   (network)
"""
import os, re, subprocess, sys

VERSION = 'sonnet-2026-09-22'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, 'data', VERSION)
os.makedirs(DATA_DIR, exist_ok=True)
UA = 'wikipedia-open-problems-audit/1.0 (research; contact via repository)'
RAW = 'https://en.wikipedia.org/w/index.php?title=List_of_unsolved_problems_in_mathematics&oldid=%d&action=raw'

SNAPSHOT = 1199136318

REF_PAIR = re.compile(r'<ref\b[^>]*?(?<!/)>.*?</ref\s*>', re.S | re.I)
REF_SELF = re.compile(r'<ref\b[^>]*/\s*>', re.S | re.I)


def strip_refs(t):
    """Remove every <ref>...</ref> and <ref ... />. Nothing else is touched."""
    prev = None
    while prev != t:                      # nested <ref> inside <ref> does occur on this page
        prev = t
        t = REF_PAIR.sub('', t)
    return REF_SELF.sub('', t)


def fetch(oldid):
    r = subprocess.run(['curl', '-s', '-m', '120', '-H', f'User-Agent: {UA}', RAW % oldid],
                       capture_output=True, text=True)
    if len(r.stdout) < 10000:
        sys.exit(f'fetch of {oldid} returned {len(r.stdout)} bytes')
    return r.stdout


for oldid, name in [(SNAPSHOT, 'page.wiki')]:
    raw = fetch(oldid)
    out = strip_refs(raw)
    open(os.path.join(DATA_DIR, name), 'w', encoding='utf-8').write(out)
    print(f'{oldid} -> {name}: {len(raw)} raw, {len(out)} stripped, '
          f'{out.count("* ")} bullets, refs left: {out.lower().count("<ref")}')
