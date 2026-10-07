#!/usr/bin/env bash
# Tests for commit_and_push.sh against throwaway local repositories (no network).
# Scenario 1 reproduces the 2026-10-07 failure: the first push is rejected by
# the server, another commit lands meanwhile, and the working tree holds an
# unstaged deletion of a tracked file.
set -euo pipefail

script="$(cd "$(dirname "$0")" && pwd)/commit_and_push.sh"
root="$(mktemp -d)"
trap 'rm -rf "$root"' EXIT
export PUSH_BACKOFF_SECONDS=0 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.invalid \
  GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.invalid
fail() { echo "FAIL: $*"; exit 1; }

# Fresh bare remote with one commit: data.txt plus a tracked raw.json.gz.
setup() {
  rm -rf "$root"/*
  git init -q --bare -b main "$root/remote.git"
  git clone -q "file://$root/remote.git" "$root/seed" 2>/dev/null
  (cd "$root/seed" && echo a > data.txt && echo raw > raw.json.gz \
    && git add . && git commit -qm seed && git push -q origin main)
  git clone -q --depth 1 "file://$root/remote.git" "$root/runner"
}

# Push a commit from another clone (a concurrent run or a manual edit).
other_commit() {
  git clone -q "file://$root/remote.git" "$root/other"
  (cd "$root/other" && echo "$2" > "$1" && git add . && git commit -qm "other: $1" \
    && git push -q origin main)
}

# Make the remote reject the next $1 pushes, like GitHub's HTTP 500.
reject_pushes() {
  echo "$1" > "$root/remote.git/rejects-left"
  cat > "$root/remote.git/hooks/pre-receive" <<'HOOK'
#!/usr/bin/env bash
n=$(cat rejects-left)
if [ "$n" -gt 0 ]; then echo $((n - 1)) > rejects-left; echo "Internal Server Error"; exit 1; fi
HOOK
  chmod +x "$root/remote.git/hooks/pre-receive"
}

echo "== 1: rejected push + concurrent commit + unstaged deletion"
setup
other_commit other.txt x
reject_pushes 1
(cd "$root/runner" && rm raw.json.gz && echo b > data.txt \
  && "$script" "pipeline update" data.txt missing-dir/) || fail "script exited non-zero"
log=$(git -C "$root/remote.git" log --format=%s main)
grep -qx "pipeline update" <<<"$log" || fail "pipeline commit not on remote"
grep -qx "other: other.txt" <<<"$log" || fail "concurrent commit lost"
git -C "$root/remote.git" cat-file -e main:raw.json.gz || fail "unstaged deletion was committed"
[ "$(git -C "$root/remote.git" show main:data.txt)" = b ] || fail "data.txt not updated"
echo "ok"

echo "== 2: nothing to commit"
setup
(cd "$root/runner" && "$script" "noop" data.txt) || fail "no-op run failed"
[ "$(git -C "$root/remote.git" rev-list --count main)" = 1 ] || fail "no-op made a commit"
echo "ok"

echo "== 3: conflicting concurrent write stops without pushing"
setup
other_commit data.txt c
reject_pushes 0
if (cd "$root/runner" && echo b > data.txt && "$script" "conflict" data.txt); then
  fail "conflict run should fail"
fi
[ "$(git -C "$root/remote.git" show main:data.txt)" = c ] || fail "remote was overwritten"
echo "ok"

echo "== 4: server keeps failing -> gives up after PUSH_ATTEMPTS"
setup
reject_pushes 99
if (cd "$root/runner" && echo b > data.txt && PUSH_ATTEMPTS=3 "$script" "down" data.txt); then
  fail "should fail when the server never accepts"
fi
[ "$(cat "$root/remote.git/rejects-left")" = 96 ] || fail "expected exactly 3 push attempts"
echo "ok"

echo "All commit_and_push tests passed."
