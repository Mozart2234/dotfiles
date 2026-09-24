#!/bin/sh
# Installs the agent-pulse herdr plugin from its public repo, pinned to a
# release: https://github.com/Mozart2234/herdr-agent-pulse
# The plugin's config.json is managed separately under
# dot_config/herdr/plugins/config/.
#
# run_after_ (not run_onchange_): chezmoi runs this on every apply, so a failed
# install (herdr missing, its server not running yet, no network) is retried on
# the next apply. It never fails `chezmoi apply`, and it is a no-op once the
# plugin is installed. To upgrade, bump PLUGIN_REF and run
# `herdr plugin install "$PLUGIN_SOURCE" --ref <new tag>` once by hand.
set -u

PLUGIN_ID="mozart2234.agent-pulse"
PLUGIN_SOURCE="Mozart2234/herdr-agent-pulse"
PLUGIN_REF="v0.1.0"

command -v herdr >/dev/null 2>&1 || exit 0
# The plugin itself runs on python3; without it there is nothing to install.
command -v python3 >/dev/null 2>&1 || exit 0

# `herdr plugin list --plugin` exits 0 even when the plugin is absent, so
# parse the JSON listing instead of relying on the exit code or its format.
if herdr plugin list --json 2>/dev/null | PLUGIN_ID="$PLUGIN_ID" python3 -c '
import json, os, sys
try:
    plugins = json.load(sys.stdin)["result"]["plugins"]
except (ValueError, KeyError, TypeError):
    sys.exit(1)
sys.exit(0 if any(p.get("plugin_id") == os.environ["PLUGIN_ID"] for p in plugins) else 1)
'; then
    exit 0
fi

if ! herdr plugin install "$PLUGIN_SOURCE" --ref "$PLUGIN_REF" --yes; then
    echo "agent-pulse: install failed; it will be retried on the next 'chezmoi apply'" >&2
fi
exit 0
