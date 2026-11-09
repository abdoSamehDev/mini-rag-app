#!/usr/bin/env bash
# Stop hook: after a turn that changed files in a git repo, ask Claude to check
# whether the repo's CLAUDE.md should be updated (or offer to create one).
#
# - Fires at most once per new set of changes (state kept per repo), so it never
#   nags twice about the same work and cannot loop.
# - Looks at uncommitted changes AND commits made since the last check.
# - Stays silent if CLAUDE.md was already part of the changes.
# Needs only bash and git (Git for Windows, macOS, Linux).
#
# Two copies can exist: a global one (~/.claude/hooks/) and a per-repo one
# (<repo>/.claude/hooks/, committed so clones on other machines get it). When a
# repo has its own copy, the global copy stands aside so the check runs once.

input=$(cat)

# Never re-trigger while Claude is already continuing because of a Stop hook.
if printf '%s' "$input" | grep -q '"stop_hook_active"[[:space:]]*:[[:space:]]*true'; then
  exit 0
fi

dir="${CLAUDE_PROJECT_DIR:-$PWD}"
cd "$dir" 2>/dev/null || exit 0
root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

# If the repo ships its own copy of this hook and we are not it, let that one run.
self=$(cd "$(dirname "$0")" 2>/dev/null && pwd -P)/$(basename "$0")
repo_copy="$root/.claude/hooks/claude-md-reminder.sh"
if [ -f "$repo_copy" ]; then
  repo_copy=$(cd "$(dirname "$repo_copy")" && pwd -P)/$(basename "$repo_copy")
  [ "$self" != "$repo_copy" ] && exit 0
fi

hash16() { git hash-object --stdin 2>/dev/null | cut -c1-16; }

head=$(git rev-parse HEAD 2>/dev/null || echo "none")

state_dir="$HOME/.claude/hook-state/claude-md-reminder"
mkdir -p "$state_dir" || exit 0
state_file="$state_dir/$(printf '%s' "$root" | hash16)"

prev_head="$head"
prev_sig=""
if [ -f "$state_file" ]; then
  read -r prev_head prev_sig < "$state_file"
fi

# Files changed by commits since the last check (only if history moved forward).
committed=""
if [ "$prev_head" != "$head" ] && [ "$prev_head" != "none" ] && [ "$head" != "none" ] \
   && git merge-base --is-ancestor "$prev_head" "$head" 2>/dev/null; then
  committed=$(git -c core.quotepath=off diff --name-only "$prev_head" "$head" 2>/dev/null)
fi

# Uncommitted changes (tracked + untracked, respecting .gitignore).
uncommitted=$(git -c core.quotepath=off status --porcelain 2>/dev/null | cut -c4-)
sig=$(printf '%s' "$uncommitted" | hash16)

# Remember what we have seen, before deciding anything.
printf '%s %s\n' "$head" "$sig" > "$state_file"

# Nothing new since last time -> stay quiet.
if [ -z "$committed" ] && { [ "$sig" = "$prev_sig" ] || [ -z "$uncommitted" ]; }; then
  exit 0
fi

changed=$(printf '%s\n%s\n' "$committed" "$uncommitted" | sed '/^[[:space:]]*$/d' | sort -u)
[ -z "$changed" ] && exit 0

# CLAUDE.md already touched in this batch -> assume it is being kept up to date.
if printf '%s\n' "$changed" | grep -qiE '(^|/)CLAUDE\.md$'; then
  exit 0
fi

count=$(printf '%s\n' "$changed" | wc -l | tr -d ' ')
list=$(printf '%s\n' "$changed" | head -15 | sed 's/^/- /')
[ "$count" -gt 15 ] && list="$list
- ...and $((count - 15)) more"

if [ -f "$root/CLAUDE.md" ]; then
  msg="CLAUDE.md check: this turn changed $count file(s) in $root without touching CLAUDE.md:
$list

If any of this is important project knowledge (new/changed commands, setup, config or env vars, endpoints, architecture, CI, conventions, a non-obvious bug cause or gotcha), update CLAUDE.md now in the same change and add a change-log line if the file has one. If nothing here is worth recording, do not edit anything; just end your turn without mentioning this check."
else
  msg="CLAUDE.md check: this turn changed $count file(s) in $root, and this repo has no CLAUDE.md:
$list

Do not create one on your own. In one short line at the end of your reply, offer to create a CLAUDE.md for this project (overview, how to run/test, structure, conventions, gotchas, change log). If you already offered in this session, end your turn without mentioning this check."
fi

# JSON-escape the message (backslashes, quotes, tabs, newlines).
esc=$(printf '%s' "$msg" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/\t/\\t/g' | awk 'BEGIN{ORS="\\n"} {print}')
esc="${esc%\\n}"

printf '{"decision":"block","reason":"%s"}\n' "$esc"
exit 0
