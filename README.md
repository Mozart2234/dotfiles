<div align="center">

# ✨ dotfiles

**One command. Any Mac. Same setup — every time.**

Personal macOS dotfiles, managed with [chezmoi](https://chezmoi.io) — so a fresh
machine goes from zero to *my* environment without a single copy-paste.

<br>

[![chezmoi](https://img.shields.io/badge/managed%20with-chezmoi-42a5f5?style=for-the-badge&logo=chezmoi&logoColor=white)](https://chezmoi.io)
[![macOS](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)](https://www.apple.com/macos/)
[![Shell](https://img.shields.io/badge/shell-zsh-4EAA25?style=for-the-badge&logo=gnu-bash&logoColor=white)](https://www.zsh.org/)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](LICENSE)

</div>

---

## 🎯 The idea

A dotfiles folder full of loose config files is just a messy backup — you still
copy-paste it onto every machine by hand. This repo is different: it's a
**source of truth** that [chezmoi](https://chezmoi.io) renders into `$HOME`,
resolving machine-specific values (like font size) from answers prompted **once**
per machine.

Edit the source → `chezmoi apply` → done. Everywhere.

---

## 📦 What's managed

| Tool | Target | Highlights |
| :--- | :--- | :--- |
| 👻 **Ghostty** | `~/.config/ghostty/config` | Catppuccin Mocha · Victor Mono Nerd Font · per-machine font size |
| 🚀 **Starship** | `~/.config/starship.toml` | Cross-shell prompt |
| 🤖 **Claude Code** | `~/.claude/statusline.sh` | Naruto-mode statusline — model ninja, effort rank, context chakra, cost |
| 🐑 **Herdr** | `~/.config/herdr/config.toml` | Agent workspace — Catppuccin + peach, native notifications, Agent Pulse |

> [!NOTE]
> The Claude Code statusline ships as a script but isn't auto-wired. Add this to
> `~/.claude/settings.json` once per machine (that file stays local — it can hold
> machine-specific settings):
> ```json
> "statusLine": { "command": "~/.claude/statusline.sh" }
> ```

---

## 🤖 Claude Code statusline

A single line under the prompt, rendered from the session JSON Claude Code pipes
to the script on stdin, in **Naruto mode** 🍥:

```
🍃 dotfiles │ 📜 main ✱3 │ 🦊 Opus 5.5 🎖 Kage·xhigh │ 🌀 ●●●○○○○○○○ 32% │ 💰 $4.20 │ 👁 5h 41%
```

| Segment | Source field | Meaning |
| :--- | :--- | :--- |
| 🍃 village | `workspace.current_dir` | Current directory (`~` at home) |
| 📜 scroll + `✱n` | `git branch` / `git status --porcelain` | Branch and number of dirty files |
| ninja + model | `model.display_name` | 🦊 Opus (Kurama) · ⚡ Sonnet (Chidori) · 🌸 Haiku · 📜 Fable |
| 🎖 rank | `effort.level` | Genin (low) · Chūnin (medium) · Jōnin (high) · Kage (xhigh) · Hokage (max) |
| chakra bar | `context_window.used_percentage` | 🌀 < 50% · 🐸 Sennin < 80% · 🔥 Kyūbi ≥ 80% — your warning before compaction |
| 💰 ryō | `cost.total_cost_usd` | Running spend for the session |
| 👁 5h | `rate_limits.five_hour.used_percentage` | Rinnegan turns red at ≥ 80% |

Optional segments render only when their field is present, so a bare session
degrades to `🍃 dir │ 🥷 Claude`.

> [!TIP]
> Inspect the full payload with `jq` — it also carries `version`,
> `output_style.name`, `context_window.remaining_percentage`,
> `cost.total_lines_added/removed`, and `exceeds_200k_tokens`.

---

## 🐑 Herdr

[Herdr](https://herdr.dev) is a terminal workspace manager built for AI coding
agents: persistent server, workspaces, tabs, splits, and a sidebar that tracks
which agent is idle, working, or blocked on you.

The config uses Catppuccin (Mocha/Latte, following macOS appearance like
Ghostty) with Naruto-inspired peach accents: the focused pane border and
"working" agents are peach, blocked agents red.

| Key | Action |
| :--- | :--- |
| `ctrl+s` | Prefix — tmux muscle memory (tmux is no longer nested inside Herdr) |
| `prefix+alt+1..9` | Jump to agent N in the sidebar |
| `prefix+shift+j` / `k` | Next / previous agent |
| `prefix+space` | Back and forth between the last two panes |
| `prefix+v` / `prefix+minus` | Split side by side / stacked |
| `prefix+alt+g` | Lazygit in a modal popup — no pane, no split disturbed |

Beyond keys, the config turns on:

- **`[ui.toast] delivery = "terminal"`** — Herdr sends OSC 9 to Ghostty, which
  raises a native macOS notification when a background agent finishes or needs
  input (click focuses Ghostty). `"system"` would fall back to `osascript`
  without `terminal-notifier`.
- **`[ui.sound]`** — short, voiceless Naruto effects from
  `~/.config/herdr/sounds/{done,request}.mp3` (shadow-clone smoke, Sharingan).
  The clips are personal and not versioned; without them Herdr logs a
  diagnostic and plays its default sound.
- **`pane_borders = "always"`** + **`show_agent_labels_on_pane_borders`** —
  every pane gets a border whose label names the agent (and animates with Agent
  Pulse, below).
- **`panel_bg = "reset"`** — Herdr lets the terminal background (Ghostty image
  or glass) show through its panels.
- **`resume_agents_on_restore`** — after a server restart, agents return to their
  real conversation instead of an empty shell.

| Command | What it does |
| :--- | :--- |
| `herdr config check` | Validate `config.toml` |
| `herdr server reload-config` | Apply changes live — nothing restarts |
| `herdr --default-config` | Print every option, fully commented |
| `herdr channel show` / `herdr update` | Check the channel / install the latest build |

> [!WARNING]
> `herdr update` restarts the server. Run it from outside a Herdr pane, or pass
> `--handoff` — otherwise it takes down the session you're sitting in.

### Agent Pulse plugin

[herdr-agent-pulse](https://github.com/Mozart2234/herdr-agent-pulse) animates
the pane border while an agent works, puts a state icon on the tab
(`🍥` working · `🦊` needs you · `🎖` done) and writes a summary for the tab bar.
`chezmoi apply` installs it through
`.chezmoiscripts/run_after_install-herdr-agent-pulse.sh`
(pinned to a release tag, retried on every apply until it succeeds) and manages
its `config.json` (`naruto` theme, tab icons on). `config.toml` already shows
its summary on the tab bar:

```toml
tab_bar_right = [
  { type = "command", command = "cat ~/.local/state/herdr/plugins/mozart2234.agent-pulse/summary.txt 2>/dev/null", interval_seconds = 1 },
]
```

---

## 🚀 New machine

```sh
# 1 · install chezmoi
brew install chezmoi

# 2 · init + apply in one shot
#     chezmoi asks the per-machine questions, then writes everything into place
chezmoi init --apply Mozart2234/dotfiles
```

That's it. Fresh Mac, fully dressed. 🎩

---

## 🛠️ Daily workflow

| Command | What it does |
| :--- | :--- |
| `chezmoi edit ~/.config/ghostty/config` | Edit the **source** (opens the `.tmpl`) |
| `chezmoi diff` | Preview what would change in `$HOME` |
| `chezmoi apply` | Write pending changes into place |
| `chezmoi cd` | Jump into the source repo to commit & push |
| `chezmoi update` | `git pull` + `apply` — sync changes from another machine |

> [!WARNING]
> Never edit the deployed files (e.g. `~/.config/ghostty/config`) by hand — they're
> **generated**. Your edits get overwritten on the next `apply`. Always use
> `chezmoi edit`, which opens the real source.

---

## 🎨 Per-machine magic

Some values differ between machines — a low-DPI external monitor wants a slightly
smaller Ghostty font than a Retina display. chezmoi asks **once** at init and
remembers the answer locally (`~/.config/chezmoi/chezmoi.toml`, never committed):

```toml
# .chezmoi.toml.tmpl — prompted at `chezmoi init`
[data]
    lowDpi = {{ promptBoolOnce . "lowDpi" "Low-DPI external monitor?" }}
```

```toml
# dot_config/ghostty/config.tmpl — reads the answer
font-size = {{ if .lowDpi }}14{{ else }}15{{ end }}
```

One source, correct on every screen. ✨

---

## 🗂️ Structure

```
.
├── .chezmoi.toml.tmpl              # per-machine prompts (font size, etc.)
├── .chezmoiignore                  # keeps README.md / LICENSE out of $HOME
├── .chezmoiscripts/
│   └── run_after_install-herdr-agent-pulse.sh  # installs the herdr plugin
├── dot_config/
│   ├── ghostty/
│   │   └── config.tmpl             # → ~/.config/ghostty/config
│   ├── herdr/
│   │   ├── config.toml             # → ~/.config/herdr/config.toml
│   │   └── plugins/config/mozart2234.agent-pulse/
│   │       └── config.json         # → agent-pulse theme and options
│   └── starship.toml               # → ~/.config/starship.toml
├── dot_claude/
│   └── executable_statusline.sh    # → ~/.claude/statusline.sh (+x preserved)
├── dot_zsh/
│   └── completions/_herdr          # → ~/.zsh/completions/_herdr (on fpath before compinit)
├── LICENSE
└── README.md
```

<details>
<summary><b>chezmoi naming cheatsheet</b></summary>

<br>

chezmoi maps source names to targets by convention:

| Source prefix | Meaning | Example → Target |
| :--- | :--- | :--- |
| `dot_` | leading `.` | `dot_config` → `~/.config` |
| `executable_` | sets `+x` | `executable_statusline.sh` → executable file |
| `.tmpl` | Go template | rendered with your machine's data |

</details>

---

<div align="center">

Made with ☕ by [Alexei Mamani](https://github.com/Mozart2234) · [MIT](LICENSE)

</div>
