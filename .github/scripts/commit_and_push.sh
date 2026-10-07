#!/usr/bin/env bash
# Stage the given paths, commit, and push — retrying through transient GitHub
# errors (e.g. "remote: Internal Server Error") and races with other pushes.
#
# Usage: commit_and_push.sh "<commit message>" <path> [<path> ...]
#
# Paths that don't exist are skipped, so optional outputs never fail the run.
# Unstaged changes outside the given paths are left alone: the rebase uses
# --autostash, so they can no longer block the retry (the 2026-10-07 failure).
#
# Environment overrides (used by the tests in pipeline-check.yml):
#   PUSH_REMOTE           remote name           (default: origin)
#   PUSH_BRANCH           branch to push to     (default: the checked-out branch)
#   PUSH_ATTEMPTS         push attempts         (default: 5)
#   PUSH_BACKOFF_SECONDS  base wait; attempt n waits n*n*base (default: 15)
#   PUSH_ANNOTATIONS      0 = plain errors, no Actions annotations (default: 1)
set -euo pipefail

err() {
  if [ "${PUSH_ANNOTATIONS:-1}" = 1 ]; then echo "::error::$*"; else echo "error: $*"; fi
}

message=${1:?usage: commit_and_push.sh "<message>" <path>...}
shift
remote=${PUSH_REMOTE:-origin}
branch=${PUSH_BRANCH:-$(git rev-parse --abbrev-ref HEAD)}
if [ "$branch" = "HEAD" ]; then
  err "Detached HEAD; set PUSH_BRANCH."
  exit 1
fi
attempts=${PUSH_ATTEMPTS:-5}
backoff=${PUSH_BACKOFF_SECONDS:-15}

for path in "$@"; do
  if [ -e "$path" ]; then
    git add -- "$path"
  else
    echo "skip (missing): $path"
  fi
done

if git diff --cached --quiet; then
  echo "No changes to commit."
  exit 0
fi

git commit -m "$message"

for attempt in $(seq 1 "$attempts"); do
  if git push "$remote" "HEAD:$branch"; then
    echo "Pushed on attempt $attempt."
    exit 0
  fi
  if [ "$attempt" -eq "$attempts" ]; then
    break
  fi
  wait_s=$((attempt * attempt * backoff))
  echo "Push attempt $attempt failed; retrying in ${wait_s}s."
  sleep "$wait_s"
  # Pick up anything pushed meanwhile. A rebase conflict means another run
  # wrote the same files; stop rather than guess which output is right.
  if ! git pull --rebase --autostash "$remote" "$branch"; then
    git rebase --abort 2>/dev/null || true
    err "Rebase onto $remote/$branch conflicted; not pushing."
    exit 1
  fi
done

err "Push failed after $attempts attempts."
exit 1
