#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Sodra/DAIA.git}"
BRANCH="${BRANCH:-main}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-30}"

cd /repo

git config --global --add safe.directory /repo

echo "[updater] Tracking $REPO_URL ($BRANCH), polling every ${INTERVAL_SECONDS}s"

while true; do
  if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "[updater] /repo is not a git repo. Sleeping."
    sleep "$INTERVAL_SECONDS"
    continue
  fi

  remote_hash=$(git ls-remote "$REPO_URL" "refs/heads/$BRANCH" | awk '{print $1}')
  local_hash=$(git rev-parse HEAD 2>/dev/null || true)

  if [ -n "$remote_hash" ] && [ "$remote_hash" != "$local_hash" ]; then
    echo "[updater] Change detected: $local_hash -> $remote_hash"
    git fetch origin "$BRANCH"
    if git merge --ff-only "origin/$BRANCH"; then
      echo "[updater] Repo updated. Rebuilding daia..."
      docker compose build daia
      docker compose up -d --no-deps --force-recreate daia
      echo "[updater] daia restarted."
    else
      echo "[updater] Fast-forward merge failed. Skipping update."
    fi
  fi

  sleep "$INTERVAL_SECONDS"
done
