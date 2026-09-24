import unittest

from agent_pulse import core


class ThemeResolutionTests(unittest.TestCase):
    def test_unknown_theme_falls_back_to_iterm(self):
        self.assertEqual(core.resolve_theme("not-a-real-theme"), "iterm")
        self.assertEqual(core.resolve_theme(None), "iterm")

    def test_known_themes_pass_through(self):
        self.assertEqual(core.resolve_theme("iterm"), "iterm")
        self.assertEqual(core.resolve_theme("naruto"), "naruto")


class FrameTests(unittest.TestCase):
    def test_frame_cycles_through_iterm_frames(self):
        frames = [core.frame("iterm", tick) for tick in range(6)]
        self.assertEqual(
            frames,
            ["◐", "◓", "◑", "◒", "◐", "◓"],
        )

    def test_frame_cycles_through_naruto_frames(self):
        frames = [core.frame("naruto", tick) for tick in range(5)]
        self.assertEqual(
            frames,
            ["🍥··", "·🍥·", "··🍥", "·🍥·", "🍥··"],
        )

    def test_unknown_theme_uses_iterm_frames(self):
        self.assertEqual(core.frame("bogus", 0), core.frame("iterm", 0))


class BorderTitleTests(unittest.TestCase):
    def test_working_with_task_text(self):
        self.assertEqual(
            core.border_title("iterm", "working", 0, "refactor auth"),
            "◐ refactor auth",
        )

    def test_working_without_task_text_is_just_frame(self):
        self.assertEqual(core.border_title("iterm", "working", 2, ""), "◑")
        self.assertEqual(core.border_title("iterm", "working", 2, None), "◑")
        self.assertEqual(core.border_title("iterm", "working", 2, "   "), "◑")

    def test_working_task_text_is_trimmed(self):
        self.assertEqual(
            core.border_title("iterm", "working", 0, "  refactor auth  "),
            "◐ refactor auth",
        )

    def test_working_task_text_truncated_with_ellipsis(self):
        long_text = "x" * 100
        result = core.border_title("iterm", "working", 0, long_text)
        self.assertLessEqual(len(result), 62)
        self.assertTrue(result.endswith("…"))

    def test_blocked_with_task_text(self):
        self.assertEqual(
            core.border_title("iterm", "blocked", 0, "waiting on approval"),
            "✋ needs you · waiting on approval",
        )

    def test_blocked_without_task_text_is_just_label(self):
        self.assertEqual(core.border_title("iterm", "blocked", 0, ""), "✋ needs you")

    def test_naruto_blocked_label(self):
        self.assertEqual(core.border_title("naruto", "blocked", 0, ""), "🦊 needs you")

    def test_idle_done_unknown_return_none(self):
        for status in ("idle", "done", "unknown"):
            self.assertIsNone(core.border_title("iterm", status, 0, "anything"))


class TabLabelTests(unittest.TestCase):
    def test_compose_tab_label(self):
        self.assertEqual(core.compose_tab_label("◐", "my-tab"), "◐ my-tab")

    def test_strip_known_prefix_removes_iterm_icon(self):
        self.assertEqual(core.strip_known_prefix("◐ my-tab"), "my-tab")
        self.assertEqual(core.strip_known_prefix("✋ my-tab"), "my-tab")
        self.assertEqual(core.strip_known_prefix("✓ my-tab"), "my-tab")

    def test_strip_known_prefix_removes_naruto_icon(self):
        self.assertEqual(core.strip_known_prefix("🍥 my-tab"), "my-tab")
        self.assertEqual(core.strip_known_prefix("🦊 my-tab"), "my-tab")
        self.assertEqual(core.strip_known_prefix("🎖 my-tab"), "my-tab")

    def test_strip_known_prefix_is_idempotent(self):
        once = core.strip_known_prefix("◐ my-tab")
        twice = core.strip_known_prefix(once)
        self.assertEqual(once, twice)

    def test_strip_known_prefix_no_prefix_is_noop(self):
        self.assertEqual(core.strip_known_prefix("my-tab"), "my-tab")

    def test_switching_themes_never_stacks_prefixes(self):
        original = "my-tab"
        iterm_label = core.compose_tab_label(core.tab_icon("iterm", "working"), original)
        stripped = core.strip_known_prefix(iterm_label)
        naruto_label = core.compose_tab_label(core.tab_icon("naruto", "working"), stripped)
        self.assertEqual(core.strip_known_prefix(naruto_label), original)


class TabIconTests(unittest.TestCase):
    def test_iterm_icons(self):
        self.assertEqual(core.tab_icon("iterm", "working"), "◐")
        self.assertEqual(core.tab_icon("iterm", "blocked"), "✋")
        self.assertEqual(core.tab_icon("iterm", "done"), "✓")

    def test_naruto_icons(self):
        self.assertEqual(core.tab_icon("naruto", "working"), "🍥")
        self.assertEqual(core.tab_icon("naruto", "blocked"), "🦊")
        self.assertEqual(core.tab_icon("naruto", "done"), "🎖")


class AggregateTabStatusTests(unittest.TestCase):
    def test_blocked_wins_over_working_and_done(self):
        self.assertEqual(
            core.aggregate_tab_status(["done", "working", "blocked"]), "blocked"
        )

    def test_working_wins_over_done(self):
        self.assertEqual(core.aggregate_tab_status(["done", "working"]), "working")

    def test_done_wins_over_idle(self):
        self.assertEqual(core.aggregate_tab_status(["idle", "done"]), "done")

    def test_empty_or_all_idle_is_idle(self):
        self.assertEqual(core.aggregate_tab_status([]), "idle")
        self.assertEqual(core.aggregate_tab_status(["idle", "idle"]), "idle")

    def test_unknown_statuses_do_not_count_as_active(self):
        self.assertEqual(core.aggregate_tab_status(["unknown", "unknown"]), "idle")


class SummaryTests(unittest.TestCase):
    def test_summary_counts_working_and_blocked(self):
        statuses = ["working", "working", "blocked", "idle"]
        self.assertEqual(core.summary("iterm", statuses), "◐ 2 · ✋ 1")

    def test_summary_includes_done_only_when_nonzero(self):
        statuses = ["working", "done", "done"]
        self.assertEqual(core.summary("iterm", statuses), "◐ 1 · ✓ 2")

    def test_summary_empty_when_nothing_active(self):
        self.assertEqual(core.summary("iterm", ["idle", "unknown"]), "")

    def test_summary_uses_naruto_icons(self):
        self.assertEqual(core.summary("naruto", ["working", "blocked"]), "🍥 1 · 🦊 1")


if __name__ == "__main__":
    unittest.main()
