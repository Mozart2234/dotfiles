# agent-pulse

A local herdr plugin that makes agent activity visible inside herdr, without
any Ghostty or herdr source changes:

- An animated pane-border title while an agent is working (a spinner frame
  plus its current task text, read from the pane's own terminal title).
- A static "needs you" border label while an agent is blocked.
- A state icon prefixed onto a tab's label whenever any pane in that tab is
  working, blocked, or done; the tab's original label is restored once
  nothing in it is active.
- A one-line summary (e.g. `◐ 2 · ✋ 1`) written to a file for
  `ui.tab_bar_right` to display.

Two themes are built in: `iterm` (default, iTerm2-style glyphs) and `naruto`
(a bouncing rasengan spinner). Unknown theme names fall back to `iterm`.

## How it works

A small background daemon (`agent_pulse/daemon.py`) subscribes to herdr's
socket API for `pane.agent_status_changed`, tracks each pane's status, and
reports presentation-only metadata (`pane.report_metadata`, `tab.rename`)
back to herdr. `bin/ensure-daemon` is the plugin's `[[startup]]` and
`[[events]]` hook: it is invoked constantly (on every
`pane.agent_status_changed`, unsupervised, up to 32 concurrent), so it does
almost nothing -- check whether the daemon's pidfile is alive, and if not,
launch `python3 -m agent_pulse.daemon` detached. The daemon itself owns the
socket connection, the animation loop, and its own singleton lock (a
`flock()` on its pidfile), so a burst of concurrent hook invocations is safe.

All reported titles carry a short TTL, so if the daemon dies, any pane it
was animating returns to normal within about a second on its own -- no
stuck spinners.

## Install

```sh
herdr plugin link ~/.config/herdr/plugins/agent-pulse
```

`[[startup]]` only runs herdr's own server boot or a live handoff, not
`plugin link`/`enable` -- the daemon starts the first time any pane's agent
status changes after linking. To start it immediately after linking a
running herdr, trigger any agent status change (or restart herdr).

## Configure

Create `$HERDR_PLUGIN_CONFIG_DIR/config.json` (see `config.default.json` in
this directory for the documented defaults):

```json
{
  "theme": "iterm",
  "fps": 4,
  "tab_icons": true
}
```

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `theme` | `"iterm"` \| `"naruto"` | `"iterm"` | Unknown values fall back to `iterm`. |
| `fps` | integer | `4` | Animation frame rate, clamped to 1-8. |
| `tab_icons` | boolean | `true` | Set `false` to disable tab-label renaming (border animation and the summary file are unaffected). |

A missing file, missing keys, or malformed JSON all fall back to the
defaults above rather than failing.

For plugin id `local.agent-pulse`, herdr resolves this to (verified against
v0.9.1 `src/plugin_paths.rs`, which percent-encodes anything outside
`[a-z0-9._-]`; `local.agent-pulse` needs no encoding):

```
~/.config/herdr/plugins/config/local.agent-pulse/config.json
```

## Add the tab-bar-right summary

herdr passes each plugin its own `$HERDR_PLUGIN_STATE_DIR`, which for
`local.agent-pulse` resolves to:

```
~/.local/state/herdr/plugins/local.agent-pulse/
```

The daemon writes `summary.txt` there (atomically, only when it changes; the
last line is always the current summary, or an empty line when nothing is
active). Add this to `~/.config/herdr/config.toml`:

```toml
[[ui.tab_bar_right]]
type = "command"
command = "cat ~/.local/state/herdr/plugins/local.agent-pulse/summary.txt 2>/dev/null"
interval_seconds = 1
```

(herdr strips ANSI and shows the last completed output line, so a plain
`cat` is enough.)

## Limitations

- **Tab renames are sticky.** herdr's `tab.rename` sets a permanent custom
  label (no clear option, and the tab turns bold and stops auto-following
  cwd/git) until renamed again. This plugin restores the original label once
  a tab goes idle, but while a tab has an icon, it behaves like any other
  manually-renamed tab.
- **Pane-border color is not configurable.** herdr's border color is
  focus-only; this plugin only changes the *title text* shown on the
  border, not its color.
- **New panes take up to a couple of animation ticks to appear live.** A
  brand-new pane's status is known immediately (from the `pane.created`
  event's own payload), but it only gets its own live status-change
  subscription after the daemon's next topology-triggered reconnect, which
  happens as soon as the daemon notices the new pane -- not on a fixed
  delay, but not instantaneous either.

## Disable / uninstall

```sh
herdr plugin disable local.agent-pulse   # keeps it linked, stops running it
herdr plugin unlink local.agent-pulse    # removes it entirely
```

Disabling or unlinking does not by itself stop an already-running daemon
process; killing it (or waiting for its next report to hit a closed
connection) clears any titles/tab renames it owned, since it runs the same
graceful-shutdown path as SIGTERM/SIGINT.

## Development

```sh
cd agent-pulse
python3 -m unittest discover -s tests -v
```

Requires Python 3.9+ (stdlib only, no third-party dependencies). Tests spin
up a fake herdr socket server in a temp directory; they never touch a real
herdr instance.
