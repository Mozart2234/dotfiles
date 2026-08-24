#!/bin/bash
# Claude Code statusline · Catppuccin Mocha · Nerd Font icons
# Reads the session JSON from stdin and prints a single status line.

input=$(cat)

# ── Catppuccin Mocha truecolor helpers ─────────────────────────────
c() { printf '\033[38;2;%sm' "$1"; }
RESET='\033[0m'
BLUE="137;180;250"
MAUVE="203;166;247"
GREEN="166;227;161"
PEACH="250;179;135"
RED="243;139;168"
TEAL="148;226;213"
LAVENDER="180;190;254"
SURFACE="88;91;112"
SEP="  $(c "$SURFACE")·$RESET  "

# ── Data: one jq pass, one field per line (empty fields preserved) ─
fields=()
while IFS= read -r line; do fields+=("$line"); done < <(
  printf '%s' "$input" | jq -r '[
    (.model.display_name // "Claude"),
    (.workspace.current_dir // .cwd // ""),
    (.worktree.name // ""),
    (.worktree.branch // ""),
    (.context_window.used_percentage // ""),
    (.cost.total_cost_usd // ""),
    (.vim.mode // ""),
    (.agent.name // "")
  ] | .[]'
)
model="${fields[0]}"
cwd="${fields[1]}"
wt_name="${fields[2]}"
wt_branch="${fields[3]}"
used="${fields[4]}"
cost="${fields[5]}"
vim_mode="${fields[6]}"
agent="${fields[7]}"

# Directory label: worktree name wins, else the last path component
dir_base="${cwd##*/}"
[ "$cwd" = "$HOME" ] && dir_base="~"
[ -n "$wt_name" ] && dir_base="$wt_name"

# Git: single call gives branch and dirty state at once
branch="$wt_branch"
dirty=""
if [ -n "$cwd" ]; then
  porcelain=$(git -C "$cwd" --no-optional-locks status --porcelain=v1 -b 2>/dev/null)
  if [ -n "$porcelain" ]; then
    [ -n "$branch" ] || branch=$(printf '%s' "$porcelain" | head -1 | sed -n 's/^## \([^.]*\).*/\1/p')
    # Line 1 is the "## branch" header; anything after it means changes.
    [ -n "$(printf '%s\n' "$porcelain" | sed '1d' | head -1)" ] && dirty="✗"
  fi
fi

# ── Render ─────────────────────────────────────────────────────────
out="$(c "$BLUE")󰉋 ${dir_base}$RESET"

if [ -n "$branch" ]; then
  out="$out$SEP$(c "$GREEN")  ${branch}$RESET"
  [ -n "$dirty" ] && out="$out $(c "$PEACH")${dirty}$RESET"
fi

out="$out$SEP$(c "$MAUVE")󰚩 ${model}$RESET"
[ -n "$agent" ] && out="$out $(c "$LAVENDER")→ ${agent}$RESET"

if [ -n "$used" ]; then
  used_int=$(printf "%.0f" "$used")
  filled=$(( used_int / 10 ))
  [ "$filled" -gt 10 ] && filled=10
  bar=""
  i=0
  while [ "$i" -lt 10 ]; do
    if [ "$i" -lt "$filled" ]; then bar="${bar}█"; else bar="${bar}░"; fi
    i=$(( i + 1 ))
  done

  if   [ "$used_int" -ge 80 ]; then bar_color="$RED"
  elif [ "$used_int" -ge 50 ]; then bar_color="$PEACH"
  else bar_color="$GREEN"; fi

  out="$out$SEP$(c "$bar_color")${bar} ${used_int}%$RESET"
fi

if [ -n "$cost" ]; then
  out="$out$SEP$(c "$TEAL")\$$(printf '%.2f' "$cost")$RESET"
fi

[ -n "$vim_mode" ] && out="$out$SEP$(c "$LAVENDER")[${vim_mode}]$RESET"

printf '%b' "$out"
