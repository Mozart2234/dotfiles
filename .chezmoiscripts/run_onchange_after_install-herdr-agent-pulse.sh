#!/bin/sh
# Installs the agent-pulse herdr plugin from its public repo:
# https://github.com/Mozart2234/herdr-agent-pulse
# chezmoi re-runs this only when this file changes. The plugin's config.json
# is managed separately under dot_config/herdr/plugins/config/.
#
# Never fails `chezmoi apply`: herdr may be missing, or its server not running
# yet on a fresh machine. Re-run with `chezmoi apply` or install by hand later.
set -u

PLUGIN_ID="mozart2234.agent-pulse"
PLUGIN_SOURCE="Mozart2234/herdr-agent-pulse"

command -v herdr >/dev/null 2>&1 || exit 0

# `herdr plugin list --plugin` exits 0 even when the plugin is absent, so
# look for the id in the JSON output instead.
if herdr plugin list --plugin "$PLUGIN_ID" --json 2>/dev/null | grep -q "\"plugin_id\":\"$PLUGIN_ID\""; then
    exit 0
fi

if ! herdr plugin install "$PLUGIN_SOURCE" --yes; then
    echo "agent-pulse: install failed; run 'herdr plugin install $PLUGIN_SOURCE' once herdr is running" >&2
fi
exit 0
