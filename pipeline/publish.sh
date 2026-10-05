#!/bin/sh
# Rebuild the gh-pages branch from the standalone explorer and push it. The branch holds exactly
# two files — index.html and .nojekyll — and is rewritten, not appended to, so none of main's
# history or data/ ever reaches the published repo. Run pipeline/build.py first.
#
# Usage: pipeline/publish.sh [remote]   (default: origin)
# Publishing the site from a public repo while this one stays private means adding a second remote
# — say `git remote add site git@github.com:<you>/<public-repo>.git` — and running
# `pipeline/publish.sh site`. Only the two files above are ever sent to it.
set -e
REMOTE=${1:-origin}
cd "$(dirname "$0")/.."
blob=$(git hash-object -w site/unsolved_problems_explorer.html)
tree=$(printf '100644 blob %s\t.nojekyll\n100644 blob %s\tindex.html\n' "$(printf '' | git hash-object -w --stdin)" "$blob" | git mktree)
git update-ref refs/heads/gh-pages "$(git commit-tree "$tree" -m "Publish the unsolved problems explorer")"
# Each run makes a fresh parentless commit, so the push is never a fast-forward.
git push --force "$REMOTE" gh-pages
