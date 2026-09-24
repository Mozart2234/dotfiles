"""Read-only smoke check: confirms the socket method names this plugin calls
still exist in the installed herdr's bundled schema. `herdr api schema` only
prints the schema document; it never touches a live server or connection.
"""

import json
import shutil
import subprocess
import unittest

REQUIRED_METHODS = [
    "pane.list",
    "pane.get",
    "pane.report_metadata",
    "tab.get",
    "tab.rename",
    "events.subscribe",
]


@unittest.skipUnless(
    shutil.which("herdr"), "herdr CLI not installed; skipping live schema smoke check"
)
class LiveSchemaSmokeTest(unittest.TestCase):
    def test_required_methods_exist_in_installed_herdr_schema(self):
        output = subprocess.check_output(
            ["herdr", "api", "schema", "--json"], text=True
        )
        schema = json.loads(output)
        methods = {
            item["properties"]["method"]["const"]
            for item in schema["schemas"]["request"]["oneOf"]
        }
        missing = [method for method in REQUIRED_METHODS if method not in methods]
        self.assertEqual(
            missing,
            [],
            "installed herdr's socket API is missing methods this plugin depends on",
        )

    def test_pane_agent_status_changed_subscription_requires_pane_id(self):
        # Verified once by reading herdr v0.9.1 source directly
        # (src/api/schema/events.rs::Subscription::PaneAgentStatusChanged);
        # this guards against a future herdr adding a wildcard filter (which
        # would make agent_pulse.daemon's per-pane subscription list and
        # reconnect-on-new-pane logic an unnecessary workaround) or removing
        # the field (which would break it outright).
        output = subprocess.check_output(
            ["herdr", "api", "schema", "--json"], text=True
        )
        schema = json.loads(output)
        subscription = schema["schemas"]["request"]["$defs"]["Subscription"]
        variant = next(
            item
            for item in subscription["oneOf"]
            if item["properties"]["type"]["const"] == "pane.agent_status_changed"
        )
        self.assertIn("pane_id", variant["required"])


if __name__ == "__main__":
    unittest.main()
