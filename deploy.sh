#!/usr/bin/env bash
set -Eeuo pipefail

step="checking the repository"
on_error() {
  local status=$?
  printf 'Deployment stopped while %s (exit %d). No further steps were run.\n' "$step" "$status" >&2
  if [[ "$step" == "pushing to origin/main" ]]; then
    printf 'The deployment commit is still local. After fixing the push error, verify the target and run: git push origin main\n' >&2
  fi
  exit "$status"
}
trap on_error ERR

cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
repo_root="$(git rev-parse --show-toplevel)"
if [[ "$repo_root" != "$PWD" ]]; then
  printf 'Deployment stopped: deploy.sh must be in the root of its Git repository.\n' >&2
  exit 1
fi

check_target() {
  local branch push_url
  branch="$(git symbolic-ref --quiet --short HEAD)" || {
    printf 'Deployment stopped: checkout the main branch first (detached HEAD).\n' >&2
    return 1
  }
  if [[ "$branch" != "main" ]]; then
    printf 'Deployment stopped: current branch is %s, not main.\n' "$branch" >&2
    return 1
  fi

  # --all catches a second push URL as well as a changed origin. Never send a
  # deployment to another repository, even if its remote is named "origin".
  push_url="$(git remote get-url --push --all origin)" || {
    printf 'Deployment stopped: origin has no usable push URL.\n' >&2
    return 1
  }
  case "$push_url" in
    https://github.com/crystal-lenard-wedding/rsvp | \
    https://github.com/crystal-lenard-wedding/rsvp.git | \
    git@github.com:crystal-lenard-wedding/rsvp.git | \
    ssh://git@github.com/crystal-lenard-wedding/rsvp.git)
      ;;
    *)
      printf 'Deployment stopped: origin push URL is not the wedding site repository: %s\n' "$push_url" >&2
      return 1
      ;;
  esac
}

check_target

status="$(git status --porcelain --untracked-files=all)"
if [[ -z "$status" ]]; then
  printf 'Nothing to deploy: there are no uncommitted changes. The version was not bumped, and nothing was pushed.\n'
  exit 0
fi

step="bumping the site version"
python3 scripts/bump-version.py

step="staging changes"
git add -A
if git diff --cached --quiet; then
  printf 'Nothing to commit after staging. No commit or push was made.\n'
  exit 0
else
  diff_status=$?
  if [[ "$diff_status" -ne 1 ]]; then
    printf 'Deployment stopped: could not inspect staged changes (exit %d).\n' "$diff_status" >&2
    exit "$diff_status"
  fi
fi

version="$(python3 -c 'import json; print(json.load(open("version.json", encoding="utf-8"))["version"])')"
step="committing the deployment"
git commit -m "Deploy wedding site version ${version}"

step="verifying the push target"
check_target

step="pushing to origin/main"
git push origin main
printf 'Pushed wedding site version %s to origin/main. GitHub Pages will update asynchronously.\n' "$version"