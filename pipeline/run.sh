#!/bin/sh
# Run one stage of the pipeline, so that a stage of several scripts is one command instead of
# several. There is deliberately no "run everything": the agent stages cost real money and the
# stages after them are worthless until you have looked at what the one before produced.
#
#   pipeline/run.sh --version V --stage fetch
#   pipeline/run.sh --version V --stage research --only kakeya-conjecture collatz-conjecture
#   pipeline/run.sh --version V --stage research --limit 5
#   pipeline/run.sh --version V --stage merge -n          # print the commands, run nothing
#
# Stages, in the order they must run:
#
#   fetch     stage_1_fetch_the_frozen_list/      the slugs, the frozen list, the Jan-2024 article
#                                                 titles, and the years Wikipedia states outright. The
#                                                 index of slugs is written first, into data/<version>/,
#                                                 because every later stage keys off it
#   research  stage_2_research_each_problem/      one agent per problem — BILLS AN API KEY unless --subscription
#   openai    stage_3_check_the_openai_repository/ the openai/math manuscripts, read from a pinned
#                                                 clone, turned into events beside the research ones
#   judge     stage_4_judge_the_records/          one agent per record — Claude Code subscription
#   years     stage_5_date_each_problem/          agents, only for problems the scrape could not
#                                                 date. OPTIONAL: the merge reads year_scraped.json
#                                                 directly, so skipping this stage keeps every year
#                                                 the fetch stage already found for free and loses
#                                                 only the researched ones.
#   merge     stage_6_merge_and_date_the_models/  merge, then date the models, then merge again
#   build     stage_7_build_the_dataset/          the dataset files and the standalone site
#   publish   stage_8_publish_the_site/           force-pushes a branch; never run by a flag
#
# `merge` runs three commands because they are a cycle: release_dates.py reads the model list out
# of research.json, and merge_research.py reads the dates back in. The first merge tolerates the
# missing file, so the order is merge, dates, merge again.
#
# Every stage is resumable: the agent passes skip problems whose record already exists, so running
# the same command again retries only what failed.
set -e

VERSION= STAGE= DRY= ONLY= LIMIT= CHECK= SAMPLE= SEED= FORCE= SUBSCRIPTION= MODEL= EFFORT= MINQ= PARALLEL=
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VERSION=$2; shift 2 ;;
    --subscription) SUBSCRIPTION=1; shift ;;
    --model)   MODEL=$2; shift 2 ;;
    --effort)  EFFORT=$2; shift 2 ;;
    --min-queries) MINQ=$2; shift 2 ;;
    --parallel) PARALLEL=$2; shift 2 ;;
    --stage)   STAGE=$2; shift 2 ;;
    --limit)   LIMIT=$2; shift 2 ;;
    --check)   CHECK=1; shift ;;
    --sample)  SAMPLE=$2; shift 2 ;;
    --seed)    SEED=$2; shift 2 ;;
    --force)   FORCE=1; shift ;;
    -n|--dry-run) DRY=1; shift ;;
    --only)    # takes the rest of the arguments, like the scripts it forwards to
      shift
      while [ $# -gt 0 ]; do
        case "$1" in --*|-n) break ;; esac
        ONLY="$ONLY $1"; shift
      done
      [ -n "$ONLY" ] || { echo "--only needs at least one key" >&2; exit 2; } ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

usage() {
  echo "usage: pipeline/run.sh --version NAME --stage STAGE [--only KEY...] [--limit N] [-n]" >&2
  echo "       stages: fetch research openai judge years merge build" >&2
  echo "       --only and --limit apply to: research judge years  (--only also: merge)" >&2
  echo "       --check  re-validates and re-collects without running an agent: research judge years" >&2
  echo "       --sample N [--seed S]  research only: N problems drawn across the whole list" >&2
  echo "       --subscription  research and merge: bill the Claude Code subscription, not the API key" >&2
  echo "       --model ID --effort LEVEL  research and judge: override the script's pinned model and effort" >&2
  echo "       --parallel N  research and judge: agents at once (defaults: research 4, judge 8)" >&2
  echo "       --min-queries N  research only: the search floor each agent is given (default 8)" >&2
  echo "       --force  years only: research again although year_posed.json is cached" >&2
}
[ -n "$VERSION" ] || { echo "no --version" >&2; usage; exit 2; }
[ -n "$STAGE" ]   || { echo "no --stage"   >&2; usage; exit 2; }

cd "$(dirname "$0")/.."

# --only and --limit are forwarded, so refuse them where the stage's scripts do not take them
# rather than silently dropping a filter the caller believed was applied.
[ -n "$SUBSCRIPTION" ] && [ "$STAGE" != research ] && [ "$STAGE" != merge ] && {
  echo "--subscription applies to research and merge (its release-date step); judge always uses the subscription" >&2; exit 2; }
[ -n "$MINQ" ] && [ "$STAGE" != research ] && {
  echo "--min-queries applies to the research stage only" >&2; exit 2; }
[ -n "$MODEL$EFFORT$PARALLEL" ] && [ "$STAGE" != research ] && [ "$STAGE" != judge ] && {
  echo "--model, --effort and --parallel apply to the research and judge stages only" >&2; exit 2; }
case "$STAGE" in
  research) ;;
  judge)
    [ -n "$SAMPLE" ] && { echo "--sample applies to the research stage; judge works on the records that exist" >&2; exit 2; } ;;
  years)
    [ -n "$SAMPLE" ] && { echo "--sample does not apply to the years stage" >&2; exit 2; } ;;
  merge)
    [ -n "$LIMIT" ] && { echo "--limit does not apply to the merge stage" >&2; exit 2; }
    [ -n "$CHECK" ] && { echo "--check does not apply to the merge stage: merge_research.py has no such mode." >&2
                         echo "to re-collect the release dates without agents, run release_dates.py --check directly" >&2
                         exit 2; } ;;
  fetch|openai|build)
    [ -n "$SAMPLE" ] && { echo "--sample does not apply to the $STAGE stage" >&2; exit 2; }
    [ -n "$ONLY" ]  && { echo "--only does not apply to the $STAGE stage: it works on the whole list" >&2; exit 2; }
    [ -n "$LIMIT" ] && { echo "--limit does not apply to the $STAGE stage: it works on the whole list" >&2; exit 2; }
    [ -n "$CHECK" ] && { echo "--check does not apply to the $STAGE stage" >&2; exit 2; } ;;
  publish)
    echo "the publish stage force-pushes a branch, so it is not run from here." >&2
    echo "look at what build produced, then: pipeline/stage_8_publish_the_site/publish.sh [remote]" >&2
    exit 2 ;;
  *) echo "unknown stage: $STAGE" >&2; usage; exit 2 ;;
esac

# run SCRIPT [extra args...] — version always; --only/--limit only where this stage accepts them.
# --force reaches only the years stage, --sample only research; the case block above has
# already refused them anywhere else, so run() can forward whatever is set.
run() {
  script=$1; shift
  set -- "$@" --version "$VERSION"
  [ -n "$ONLY" ]  && set -- "$@" --only $ONLY
  [ -n "$LIMIT" ] && set -- "$@" --limit "$LIMIT"
  [ -n "$CHECK" ]  && set -- "$@" --check
  [ -n "$SAMPLE" ] && set -- "$@" --sample "$SAMPLE"
  [ -n "$SEED" ]   && set -- "$@" --seed "$SEED"
  [ -n "$FORCE" ]  && set -- "$@" --force
  [ -n "$SUBSCRIPTION" ] && set -- "$@" --subscription
  [ -n "$MODEL" ]  && set -- "$@" --model "$MODEL"
  [ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"
  [ -n "$MINQ" ]   && set -- "$@" --min-queries "$MINQ"
  [ -n "$PARALLEL" ] && set -- "$@" --parallel "$PARALLEL"
  echo "+ python3 $script $*"
  [ -n "$DRY" ] || python3 "$script" "$@"
}

# run_plain SCRIPT [args...] — for the scripts in a stage that take no --only/--limit.
run_plain() {
  script=$1; shift
  echo "+ python3 $script $*"
  [ -n "$DRY" ] || python3 "$script" "$@"
}

echo "=== $STAGE  (version $VERSION) ==="
case "$STAGE" in
  fetch)
    run_plain pipeline/stage_1_fetch_the_frozen_list/make_problem_keys.py --version "$VERSION" 2024-01
    run_plain pipeline/stage_1_fetch_the_frozen_list/fetch_list_revision.py --version "$VERSION"
    run_plain pipeline/stage_1_fetch_the_frozen_list/fetch_article_history.py --version "$VERSION"
    run_plain pipeline/stage_1_fetch_the_frozen_list/scrape_years.py --version "$VERSION" ;;
  research)
    run pipeline/stage_2_research_each_problem/deep_dive.py ;;
  openai)
    run_plain pipeline/stage_3_check_the_openai_repository/index.py --version "$VERSION" ;;
  judge)
    run pipeline/stage_4_judge_the_records/judge.py ;;
  years)
    run pipeline/stage_5_date_each_problem/year_posed.py ;;
  merge)
    run_plain pipeline/stage_6_merge_and_date_the_models/merge_research.py --version "$VERSION"
    run      pipeline/stage_6_merge_and_date_the_models/release_dates.py
    run_plain pipeline/stage_6_merge_and_date_the_models/merge_research.py --version "$VERSION" ;;
  build)
    run_plain pipeline/stage_7_build_the_dataset/build.py --version "$VERSION" ;;
esac

case "$STAGE" in
  fetch)    NEXT="research" ;;
  research) NEXT="openai, then judge" ;;
  openai)   NEXT="judge" ;;
  judge)    NEXT="years, then merge" ;;
  years)    NEXT="merge" ;;
  merge)    NEXT="build" ;;
  build)    NEXT="review data/$VERSION/ and site/, then pipeline/stage_8_publish_the_site/publish.sh" ;;
esac
echo
echo "$STAGE done. Next: $NEXT"
