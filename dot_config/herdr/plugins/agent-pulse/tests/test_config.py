import json
import os
import tempfile
import unittest

from agent_pulse import config


class LoadConfigTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="apconfig-")
        self._old_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_defaults_when_no_config_dir_set(self):
        os.environ.pop("HERDR_PLUGIN_CONFIG_DIR", None)
        cfg = config.load()
        self.assertEqual(cfg.theme, "iterm")
        self.assertEqual(cfg.fps, 4)
        self.assertTrue(cfg.tab_icons)

    def test_defaults_when_config_file_missing(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        cfg = config.load()
        self.assertEqual(cfg.theme, "iterm")
        self.assertEqual(cfg.fps, 4)
        self.assertTrue(cfg.tab_icons)

    def test_reads_values_from_config_json(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            json.dump({"theme": "naruto", "fps": 8, "tab_icons": False}, fh)
        cfg = config.load()
        self.assertEqual(cfg.theme, "naruto")
        self.assertEqual(cfg.fps, 8)
        self.assertFalse(cfg.tab_icons)

    def test_missing_keys_fall_back_to_defaults(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            json.dump({"theme": "naruto"}, fh)
        cfg = config.load()
        self.assertEqual(cfg.theme, "naruto")
        self.assertEqual(cfg.fps, 4)
        self.assertTrue(cfg.tab_icons)

    def test_fps_is_clamped_between_1_and_8(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            json.dump({"fps": 99}, fh)
        cfg = config.load()
        self.assertEqual(cfg.fps, 8)

        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            json.dump({"fps": 0}, fh)
        cfg = config.load()
        self.assertEqual(cfg.fps, 1)

    def test_unknown_theme_in_file_falls_back_to_iterm(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            json.dump({"theme": "not-a-theme"}, fh)
        cfg = config.load()
        self.assertEqual(cfg.theme, "iterm")

    def test_malformed_json_falls_back_to_defaults(self):
        os.environ["HERDR_PLUGIN_CONFIG_DIR"] = self.tmpdir
        with open(os.path.join(self.tmpdir, "config.json"), "w") as fh:
            fh.write("{not valid json")
        cfg = config.load()
        self.assertEqual(cfg.theme, "iterm")
        self.assertEqual(cfg.fps, 4)


class StateDirTests(unittest.TestCase):
    def setUp(self):
        self._old_env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._old_env)

    def test_state_dir_from_env(self):
        os.environ["HERDR_PLUGIN_STATE_DIR"] = "/tmp/some-state-dir"
        self.assertEqual(config.state_dir(), "/tmp/some-state-dir")

    def test_state_dir_falls_back_to_default(self):
        os.environ.pop("HERDR_PLUGIN_STATE_DIR", None)
        self.assertEqual(
            config.state_dir(),
            os.path.expanduser("~/.local/state/herdr-agent-pulse"),
        )


if __name__ == "__main__":
    unittest.main()
