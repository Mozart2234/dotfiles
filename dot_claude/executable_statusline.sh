#!/bin/bash
# Custom Claude Code statusline · Catppuccin Mocha palette · Nerd Font icons
# Reads the session JSON from stdin and prints a single status line.

input=$(cat)

# ── Catppuccin Mocha truecolor helpers ─────────────────────────────
c() { printf '\033[38;2;%sm' "$1"; }   # foreground
RESET='\033[0m'
BLUE="137;180;250"
MAUVE="203;166;247"
GREEN="166;227;161"
PEACH="250;179;135"
RED="243;139;168"
TEAL="148;226;213"
SURFACE="88;91;112"
SEP="$(c "$SURFACE")·$RESET"

# ── Data ───────────────────────────────────────────────────────────
model=$(echo "$input"   | jq -r '.model.display_name // "Claude"')
cwd=$(echo "$input"     | jq -r '.workspace.current_dir // .cwd // empty')
used=$(echo "$input"    | jq -r '.context_window.used_percentage // empty')

# Directory: replace $HOME with ~, show last path component
dir="$cwd"
[ -n "$dir" ] && dir="${dir/#$HOME/~}"
dir_base="${dir##*/}"
[ "$dir" = "~" ] && dir_base="~"

# Git branch (only if inside a repo)
branch=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
fi

# ── Render ─────────────────────────────────────────────────────────
out="$(c "$BLUE")󰉋 ${dir_base}$RESET"
[ -n "$branch" ] && out="$out  $SEP  $(c "$GREEN")  ${branch}$RESET"
out="$out  $SEP  $(c "$MAUVE")󰚩 ${model}$RESET"

if [ -n "$used" ]; then
  used_int=$(printf "%.0f" "$used")
  filled=$(( used_int / 10 ))
  empty=$(( 10 - filled ))
  bar=""
  for _ in $(seq 1 "$filled"); do bar="${bar}█"; done
  for _ in $(seq 1 "$empty");  do bar="${bar}░"; done

  if   [ "$used_int" -ge 80 ]; then bar_color="$RED"
  elif [ "$used_int" -ge 50 ]; then bar_color="$PEACH"
  else bar_color="$GREEN"; fi

  out="$out  $SEP  $(c "$bar_color")${bar} ${used_int}%$RESET"
fi

printf '%b' "$out"
