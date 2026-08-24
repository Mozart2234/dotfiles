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
| 🤖 **Claude Code** | `~/.claude/statusline.sh` | Custom statusline — context, cost, git, worktree |
| 🐑 **Herdr** | `~/.config/herdr/config.toml` | Agent workspace — tmux-style keys, desktop notifications |

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
to the script on stdin.

```
󰉋 dotfiles  ·    main ✗  ·  󰚩 Opus 5 → sdd-apply  ·  ████████░░ 87%  ·  $12.50  ·  [NORMAL]
```

| Segment | Source field | Why it's there |
| :--- | :--- | :--- |
| 󰉋 directory | `worktree.name` → `workspace.current_dir` | Worktree name wins, so parallel checkouts stay distinguishable |
|  branch + `✗` | one `git status --porcelain -b` call | Branch and dirty state from a single fork |
| 󰚩 model | `model.display_name` | Which model is actually answering |
| → agent | `agent.name` | Present only while a subagent is running |
| context bar | `context_window.used_percentage` | Green < 50% · orange < 80% · red ≥ 80% — your warning before compaction |
| cost | `cost.total_cost_usd` | Running spend for the session |
| `[MODE]` | `vim.mode` | Only when vim mode is on |

Optional segments render only when their field is present, so a bare session
degrades to `󰉋 dir · 󰚩 Claude`.

> [!TIP]
> Inspect the full payload with `jq` — it also carries `version`,
> `output_style.name`, `context_window.remaining_percentage`,
> `cost.total_lines_added/removed`, and `exceeds_200k_tokens`.

<details>
<summary><b>Two bash traps this script works around</b></summary>

<br>

**Empty fields vanish with tab-separated `read`.** Tab is an *IFS whitespace
character*, so bash collapses runs of them into one delimiter even when `IFS` is
set explicitly — every optional field shifts the rest of the values left:

```sh
IFS=$'\t' read -r a b c d   # ✗ empty fields silently disappear
```

The script has `jq` emit one field per line (`| .[]`) and reads them into an
array instead.

**No `mapfile`.** macOS ships bash 3.2, which predates it. The read loop is
`while IFS= read -r line; do fields+=("$line"); done`.

</details>

---

## 🐑 Herdr

[Herdr](https://herdr.dev) is a terminal workspace manager built for AI coding
agents: persistent server, workspaces, tabs, splits, and a sidebar that tracks
which agent is idle, working, or blocked on you.

The theme and prefix come from
[Gentleman.Dots](https://github.com/Gentleman-Programming/Gentleman.Dots);
the rest is local.

| Key | Action |
| :--- | :--- |
| `ctrl+a` | Prefix — tmux/Zellij muscle memory |
| `prefix+ctrl+1..9` | Jump to agent N in the sidebar |
| `prefix+alt+j` / `k` | Next / previous agent |
| `prefix+[` / `]` | Cycle workspaces without the picker |
| `prefix+alt+g` | Lazygit in a modal popup — no pane, no split disturbed |
| `prefix+shift+g` | New git worktree (created under `~/.herdr/worktrees`) |

Beyond keys, the config turns on:

- **`[ui.toast] delivery = "system"`** — macOS notifications when a background
  agent finishes or needs input. Without it you babysit panes, which defeats the
  point of a multi-agent workspace.
- **`resume_agents_on_restore`** — after a server restart, agents return to their
  real conversation instead of an empty shell.
- **`show_agent_labels_on_pane_borders`** — which agent lives in which split,
  read straight off the border.

| Command | What it does |
| :--- | :--- |
| `herdr config check` | Validate `config.toml` |
| `herdr server reload-config` | Apply changes live — nothing restarts |
| `herdr --default-config` | Print every option, fully commented |
| `herdr channel show` / `herdr update` | Check the channel / install the latest build |

> [!WARNING]
> `herdr update` restarts the server. Run it from outside a Herdr pane, or pass
> `--handoff` — otherwise it takes down the session you're sitting in.

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
├── dot_config/
│   ├── ghostty/
│   │   └── config.tmpl             # → ~/.config/ghostty/config
│   ├── herdr/
│   │   └── config.toml             # → ~/.config/herdr/config.toml
│   └── starship.toml               # → ~/.config/starship.toml
├── dot_claude/
│   └── executable_statusline.sh    # → ~/.claude/statusline.sh (+x preserved)
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
