# dotfiles

Personal dotfiles, managed with [chezmoi](https://chezmoi.io).

The source of truth lives in this repo. chezmoi renders each source file to its
target path in `$HOME`, resolving machine-specific values (like Ghostty's
font size) from data prompted once per machine at init time.

## What's managed

| Tool                 | Target                      | Notes                                     |
| -------------------- | --------------------------- | ----------------------------------------- |
| Ghostty              | `~/.config/ghostty/config`  | Catppuccin Mocha, Victor Mono Nerd Font   |
| Starship             | `~/.config/starship.toml`   | Prompt config                             |
| Claude Code status   | `~/.claude/statusline.sh`   | Custom statusline (executable)            |

> The Claude Code statusline needs to be wired in `~/.claude/settings.json`:
> `"statusLine": { "command": "~/.claude/statusline.sh" }`. That file is not
> managed here (it can hold machine-specific settings), so set it once per machine.

## New machine

```sh
# 1. Install chezmoi (macOS)
brew install chezmoi

# 2. Init from this repo and apply in one step.
#    chezmoi will ask the per-machine questions (e.g. low-DPI monitor).
chezmoi init --apply Mozart2234/dotfiles
```

## Daily use

```sh
chezmoi edit ~/.config/ghostty/config   # edit the SOURCE (opens the .tmpl)
chezmoi diff                            # preview what would change
chezmoi apply                           # write changes to $HOME
chezmoi cd                              # jump into the source repo to commit/push
```

## Pull changes made on another machine

```sh
chezmoi update    # git pull + apply
```

## Machine-specific values

Per-machine answers (e.g. whether this is a low-DPI external monitor) are
prompted once at `chezmoi init` and stored locally in
`~/.config/chezmoi/chezmoi.toml` — never committed. Templates read them via
`.chezmoi` data. See `.chezmoi.toml.tmpl` for the prompts and
`dot_config/ghostty/config.tmpl` for how they're used.
