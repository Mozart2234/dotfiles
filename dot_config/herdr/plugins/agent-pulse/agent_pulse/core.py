"""Pure, side-effect-free logic for agent-pulse.

Themes, animation frames, tab-label composition, tab-status aggregation, and
the tab-bar-right summary string. Nothing in this module touches the herdr
socket, the filesystem, or the clock beyond an injected tick/index.
"""

from typing import Dict, List, Optional, Sequence

DEFAULT_THEME = "iterm"

MAX_TASK_TEXT_CHARS = 60

_THEMES = {
    "iterm": {
        "working_frames": ["◐", "◓", "◑", "◒"],
        "icons": {
            "working": "◐",
            "blocked": "✋",
            "done": "✓",
        },
        "blocked_label": "✋ needs you",
    },
    "naruto": {
        "working_frames": ["\U0001f365··", "·\U0001f365·", "··\U0001f365", "·\U0001f365·"],
        "icons": {
            "working": "\U0001f365",
            "blocked": "\U0001f98a",
            "done": "\U0001f396",
        },
        "blocked_label": "\U0001f98a needs you",
    },
}

# Status priority for tab-level aggregation: first match wins.
_STATUS_PRIORITY = ("blocked", "working", "done")


def resolve_theme(theme: Optional[str]) -> str:
    """Return a known theme name, falling back to the default for anything else."""
    if theme in _THEMES:
        return theme
    return DEFAULT_THEME


def frame(theme: str, tick: int) -> str:
    """Return the working-frame glyph for this tick, cycling through the theme's frames."""
    frames = _THEMES[resolve_theme(theme)]["working_frames"]
    return frames[tick % len(frames)]


def tab_icon(theme: str, status: str) -> Optional[str]:
    """Return the tab-label icon for a status (working/blocked/done), or None if not iconified."""
    return _THEMES[resolve_theme(theme)]["icons"].get(status)


def _truncate(text: str, max_chars: int = MAX_TASK_TEXT_CHARS) -> str:
    text = text.strip()
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[: max_chars - 1].rstrip() + "…"


def border_title(
    theme: str, status: str, tick: int, task_text: Optional[str]
) -> Optional[str]:
    """Compose the pane-border title for a status, or None when the border should clear."""
    theme = resolve_theme(theme)
    text = _truncate(task_text) if task_text else ""

    if status == "working":
        current_frame = frame(theme, tick)
        return f"{current_frame} {text}" if text else current_frame

    if status == "blocked":
        label = _THEMES[theme]["blocked_label"]
        return f"{label} · {text}" if text else label

    # idle, done, unknown: no border override, clear it.
    return None


def compose_tab_label(icon: str, original: str) -> str:
    """Prefix a tab's original label with a state icon."""
    return f"{icon} {original}"


def _known_icon_prefixes() -> List[str]:
    icons = set()
    for theme in _THEMES.values():
        icons.update(theme["icons"].values())
    # Longest first so a multi-character icon is never left partially stripped.
    return sorted(icons, key=len, reverse=True)


def strip_known_prefix(label: str) -> str:
    """Remove a leading icon (from any known theme) and its separating space.

    Idempotent: calling this twice yields the same result as calling it once,
    so switching themes or restarting after a crash never stacks icons.
    """
    for icon in _known_icon_prefixes():
        prefix = f"{icon} "
        if label.startswith(prefix):
            return label[len(prefix):]
    return label


def aggregate_tab_status(statuses: Sequence[str]) -> str:
    """Reduce a tab's pane statuses to one status: blocked > working > done > idle."""
    present = set(statuses)
    for status in _STATUS_PRIORITY:
        if status in present:
            return status
    return "idle"


def summary(theme: str, statuses: Sequence[str]) -> str:
    """Build the tab-bar-right summary string, e.g. '◐ 2 · ✋ 1'."""
    theme = resolve_theme(theme)
    icons = _THEMES[theme]["icons"]
    counts = {
        "working": 0,
        "blocked": 0,
        "done": 0,
    }
    for status in statuses:
        if status in counts:
            counts[status] += 1

    parts = []
    for status in ("working", "blocked", "done"):
        count = counts[status]
        if count > 0:
            parts.append(f"{icons[status]} {count}")
    return " · ".join(parts)
