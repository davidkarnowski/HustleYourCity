#!/usr/bin/env bash
# Keep one raw City export per ISO week in a draft (collaborators-only)
# release, pruning the oldest beyond SNAPSHOT_KEEP_WEEKS. Raw exports never go
# into git; this is their only retention.
#
# Usage: snapshot_raw_export.sh            (run from the repo root, after export)
#
# Environment:
#   GH_TOKEN             token with contents: write (releases)
#   SNAPSHOT_RELEASE     release tag             (default: raw-snapshots-weekly)
#   SNAPSHOT_KEEP_WEEKS  weeks to keep           (default: 12)
#   SNAPSHOT_WEEK        override ISO week, e.g. 2026-W41 (tests only)
#   SNAPSHOT_FILE        override the export file        (tests only)
set -euo pipefail

release=${SNAPSHOT_RELEASE:-raw-snapshots-weekly}
keep=${SNAPSHOT_KEEP_WEEKS:-12}
week=${SNAPSHOT_WEEK:-$(date -u +%G-W%V)}
latest=${SNAPSHOT_FILE:-$(ls -1 data/service_requests_full_*.json.gz 2>/dev/null | sort | tail -n 1 || true)}

if [ -z "$latest" ] || [ ! -f "$latest" ]; then
  echo "No raw export found; nothing to snapshot."
  exit 0
fi

if ! gh release view "$release" >/dev/null 2>&1; then
  gh release create "$release" --draft \
    --title "Raw City exports — weekly, last $keep weeks" \
    --notes "One full service-request export per ISO week, kept for $keep weeks. Managed by .github/scripts/snapshot_raw_export.sh."
fi

assets=$(gh release view "$release" --json assets -q '.assets[].name')
if grep -q "^service_requests_${week}_" <<<"$assets"; then
  echo "Week $week already saved."
else
  stamp=$(basename "$latest" .json.gz | sed 's/^service_requests_full_//')
  name="service_requests_${week}_${stamp}.json.gz"
  cp "$latest" "${RUNNER_TEMP:-/tmp}/$name"
  gh release upload "$release" "${RUNNER_TEMP:-/tmp}/$name"
  rm -f "${RUNNER_TEMP:-/tmp}/$name"
  echo "Saved $name to draft release $release."
  assets=$(printf '%s\n%s\n' "$assets" "$name")
fi

# Names start with the ISO week, so a plain sort is oldest-first.
{ grep -E '^service_requests_[0-9]{4}-W[0-9]{2}_' <<<"$assets" || true; } | sort | head -n -"$keep" \
  | while read -r old; do
      gh release delete-asset "$release" "$old" --yes
      echo "Pruned $old."
    done
