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
| 🤖 **Claude Code** | `~/.claude/statusline.sh` | Custom statusline (executable) |

> [!NOTE]
> The Claude Code statusline ships as a script but isn't auto-wired. Add this to
> `~/.claude/settings.json` once per machine (that file stays local — it can hold
> machine-specific settings):
> ```json
> "statusLine": { "command": "~/.claude/statusline.sh" }
> ```

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
