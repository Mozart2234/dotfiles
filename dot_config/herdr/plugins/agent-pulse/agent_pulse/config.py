"""Config loading for agent-pulse.

herdr passes `HERDR_PLUGIN_CONFIG_DIR` and `HERDR_PLUGIN_STATE_DIR` to every
plugin command (verified: src/app/api/plugins/env.rs::plugin_path_env). We
read an optional `config.json` from the config dir; a missing file, missing
keys, or malformed JSON all fall back to defaults rather than failing.
"""

import json
import os

from agent_pulse import core

DEFAULT_THEME = core.DEFAULT_THEME
DEFAULT_FPS = 4
DEFAULT_TAB_ICONS = True
MIN_FPS = 1
MAX_FPS = 8

CONFIG_FILE_NAME = "config.json"
DEFAULT_STATE_DIR = "~/.local/state/herdr-agent-pulse"


class Config(object):
    def __init__(self, theme, fps, tab_icons):
        self.theme = theme
        self.fps = fps
        self.tab_icons = tab_icons


def _clamp_fps(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return DEFAULT_FPS
    return max(MIN_FPS, min(MAX_FPS, value))


def config_dir():
    override = os.environ.get("HERDR_PLUGIN_CONFIG_DIR")
    if override:
        return override
    return None


def state_dir():
    override = os.environ.get("HERDR_PLUGIN_STATE_DIR")
    if override:
        return override
    return os.path.expanduser(DEFAULT_STATE_DIR)


def load():
    """Load config.json from HERDR_PLUGIN_CONFIG_DIR, defaults on any problem."""
    data = {}
    directory = config_dir()
    if directory:
        path = os.path.join(directory, CONFIG_FILE_NAME)
        try:
            with open(path, "r") as fh:
                data = json.load(fh)
        except (IOError, OSError, ValueError):
            data = {}
        if not isinstance(data, dict):
            data = {}

    theme = core.resolve_theme(data.get("theme", DEFAULT_THEME))
    fps = _clamp_fps(data.get("fps", DEFAULT_FPS))
    tab_icons = bool(data.get("tab_icons", DEFAULT_TAB_ICONS))
    return Config(theme=theme, fps=fps, tab_icons=tab_icons)
