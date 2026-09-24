#!/bin/bash
# Claude Code statusline · Naruto mode 🍥
# Reads the session JSON from stdin and prints a single status line.

input=$(cat)

c() { printf '\033[38;2;%sm' "$1"; }
RESET='\033[0m'; BOLD='\033[1m'
ORANGE="255;140;0"      # Naruto jumpsuit
BLUE="70;130;220"       # Rasengan
LEAF="120;200;90"       # Konoha
RED="220;50;50"         # Kurama / Sharingan
PURPLE="160;110;220"    # Rinnegan
GOLD="240;200;80"       # Ryō
GREY="110;110;120"
SEP="$(c "$GREY")│$RESET"

j() { echo "$input" | jq -r "$1 // empty"; }
model=$(j '.model.display_name');  model=${model:-Claude}
cwd=$(j '.workspace.current_dir'); cwd=${cwd:-$(j '.cwd')}
used=$(j '.context_window.used_percentage')
cost=$(j '.cost.total_cost_usd')
rl5=$(j '.rate_limits.five_hour.used_percentage')
effort=$(j '.effort.level')

# Model → ninja
case "$model" in
  *Opus*)   ninja="🦊" ;;   # Kurama
  *Sonnet*) ninja="⚡" ;;   # Chidori
  *Haiku*)  ninja="🌸" ;;   # Sakura
  *Fable*)  ninja="📜" ;;   # Jiraiya's novels
  *)        ninja="🥷" ;;
esac

# Village = current dir
dir="${cwd/#$HOME/~}"; village="${dir##*/}"; [ "$dir" = "~" ] && village="~"

# Scroll = git branch + dirty marker
scroll=""
if [ -n "$cwd" ] && git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git -C "$cwd" --no-optional-locks branch --show-current 2>/dev/null)
  dirty=$(git -C "$cwd" --no-optional-locks status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  scroll="$(c "$LEAF")📜 ${branch:-detached}$RESET"
  [ "$dirty" -gt 0 ] && scroll="$scroll $(c "$ORANGE")✱${dirty}$RESET"
fi

out="$(c "$LEAF")🍃 ${village}$RESET"
[ -n "$scroll" ] && out="$out $SEP $scroll"
out="$out $SEP $(c "$ORANGE")${BOLD}${ninja} ${model}$RESET"

# Rank = effort level
if [ -n "$effort" ]; then
  case "$effort" in
    low)    rank="Genin" ;;
    medium) rank="Chūnin" ;;
    high)   rank="Jōnin" ;;
    xhigh)  rank="Kage" ;;
    max)    rank="Hokage" ;;
    *)      rank="$effort" ;;
  esac
  out="$out $(c "$GOLD")🎖 ${rank}·${effort}$RESET"
fi

# Chakra = context used
if [ -n "$used" ]; then
  u=$(printf "%.0f" "$used")
  filled=$(( u / 10 )); bar=""
  for ((i=0;i<10;i++)); do [ $i -lt $filled ] && bar+="●" || bar+="○"; done
  if   [ "$u" -ge 80 ]; then col="$RED";    mode="🔥 Kyūbi"
  elif [ "$u" -ge 50 ]; then col="$ORANGE"; mode="🐸 Sennin"
  else                       col="$BLUE";   mode="🌀"; fi
  out="$out $SEP $(c "$col")${mode} ${bar} ${u}%$RESET"
fi

# Ryō = session cost
[ -n "$cost" ] && out="$out $SEP $(c "$GOLD")💰 \$$(printf '%.2f' "$cost")$RESET"

# Rinnegan = 5h rate limit
if [ -n "$rl5" ]; then
  r=$(printf "%.0f" "$rl5"); rc="$PURPLE"; [ "$r" -ge 80 ] && rc="$RED"
  out="$out $SEP $(c "$rc")👁 5h ${r}%$RESET"
fi

printf '%b' "$out"
