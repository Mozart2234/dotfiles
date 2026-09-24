import json
import os
import tempfile
import unittest

from agent_pulse import client as client_module
from agent_pulse import config as config_module
from agent_pulse import daemon
from tests.fake_server import FakeHerdrServer, load_fixture_result


def pane_info(pane_id, tab_id="t1", status="idle", agent="claude", title=None):
    return {
        "pane_id": pane_id,
        "tab_id": tab_id,
        "workspace_id": "w1",
        "agent_status": status,
        "agent": agent,
        "terminal_title_stripped": title,
    }


class PureHelperTests(unittest.TestCase):
    def test_frame_interval_seconds(self):
        self.assertAlmostEqual(daemon.frame_interval_seconds(4), 0.25)
        self.assertAlmostEqual(daemon.frame_interval_seconds(1), 1.0)
        self.assertAlmostEqual(daemon.frame_interval_seconds(8), 0.125)

    def test_frame_ttl_ms_has_a_floor(self):
        self.assertEqual(daemon.frame_ttl_ms(8), 1000)  # 3 * 125 = 375 -> floored to 1000
        self.assertEqual(daemon.frame_ttl_ms(1), 3000)  # 3 * 1000 = 3000

    def test_build_subscriptions_includes_lifecycle_and_per_pane_status(self):
        subs = daemon.build_subscriptions(["w1:p1", "w1:p2"])
        types = [s["type"] for s in subs]
        self.assertIn("pane.created", types)
        self.assertIn("pane.closed", types)
        self.assertIn("pane.exited", types)
        status_subs = [s for s in subs if s["type"] == "pane.agent_status_changed"]
        self.assertEqual(
            sorted(s["pane_id"] for s in status_subs), ["w1:p1", "w1:p2"]
        )

    def test_build_subscriptions_with_no_panes_is_lifecycle_only(self):
        subs = daemon.build_subscriptions([])
        self.assertEqual(len(subs), 3)


class TabLabelCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="apstate-")

    def test_set_and_get_round_trip(self):
        cache = daemon.TabLabelCache(self.tmpdir)
        cache.set("t1", "my-tab")
        self.assertEqual(cache.get("t1"), "my-tab")

    def test_persists_across_instances(self):
        daemon.TabLabelCache(self.tmpdir).set("t1", "my-tab")
        reloaded = daemon.TabLabelCache(self.tmpdir)
        self.assertEqual(reloaded.get("t1"), "my-tab")

    def test_pop_removes_entry(self):
        cache = daemon.TabLabelCache(self.tmpdir)
        cache.set("t1", "my-tab")
        cache.pop("t1")
        self.assertIsNone(cache.get("t1"))

    def test_missing_file_starts_empty(self):
        cache = daemon.TabLabelCache(self.tmpdir)
        self.assertIsNone(cache.get("anything"))
        self.assertEqual(cache.items(), [])

    def test_malformed_file_starts_empty(self):
        with open(os.path.join(self.tmpdir, daemon.TAB_LABELS_FILE_NAME), "w") as fh:
            fh.write("{not json")
        cache = daemon.TabLabelCache(self.tmpdir)
        self.assertEqual(cache.items(), [])


class SingletonLockTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="aplock-")

    def test_acquire_returns_a_lock_when_free(self):
        lock = daemon.acquire_singleton_lock(self.tmpdir)
        self.assertIsNotNone(lock)
        lock.release()

    def test_second_acquire_fails_while_first_holds_it(self):
        first = daemon.acquire_singleton_lock(self.tmpdir)
        second = daemon.acquire_singleton_lock(self.tmpdir)
        self.assertIsNone(second)
        first.release()

    def test_release_allows_reacquiring(self):
        first = daemon.acquire_singleton_lock(self.tmpdir)
        first.release()
        second = daemon.acquire_singleton_lock(self.tmpdir)
        self.assertIsNotNone(second)
        second.release()

    def test_pidfile_contains_pid_and_is_removed_on_release(self):
        lock = daemon.acquire_singleton_lock(self.tmpdir)
        pid_path = os.path.join(self.tmpdir, daemon.PID_FILE_NAME)
        with open(pid_path) as fh:
            self.assertEqual(fh.read().strip(), str(os.getpid()))
        lock.release()
        self.assertFalse(os.path.exists(pid_path))


class DaemonTestCase(unittest.TestCase):
    def setUp(self):
        self.socket_dir = tempfile.mkdtemp(prefix="apsock-", dir="/tmp")
        self.socket_path = os.path.join(self.socket_dir, "herdr.sock")
        self.server = FakeHerdrServer(self.socket_path)
        self.state_dir = tempfile.mkdtemp(prefix="apstate-")
        self.herdr_client = client_module.HerdrClient(path=self.socket_path, timeout=2.0)
        self.cfg = config_module.Config(theme="iterm", fps=4, tab_icons=True)
        self.tab_cache = daemon.TabLabelCache(self.state_dir)
        self.log_lines = []
        self.d = daemon.Daemon(
            self.herdr_client,
            self.cfg,
            self.tab_cache,
            log=self.log_lines.append,
            state_directory=self.state_dir,
        )

    def tearDown(self):
        if self.d._subscription is not None:
            self.d._subscription.close()
        self.server.stop()

    def report_calls(self):
        return [
            params
            for method, params in self.server.received_requests
            if method == "pane.report_metadata"
        ]

    def rename_calls(self):
        return [
            params
            for method, params in self.server.received_requests
            if method == "tab.rename"
        ]


class BootstrapTests(DaemonTestCase):
    def test_bootstrap_seeds_panes_from_pane_list(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", status="working")]},
        )
        self.d.bootstrap()
        self.assertIn("w1:p1", self.d.panes)
        self.assertEqual(self.d.panes["w1:p1"].status, "working")

    def test_bootstrap_subscribes_with_known_pane_ids(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1"), pane_info("w1:p2")]},
        )
        self.d.bootstrap()
        sub_request = [
            params
            for method, params in self.server.received_requests
            if method == "events.subscribe"
        ][-1]
        status_subs = [
            s for s in sub_request["subscriptions"] if s["type"] == "pane.agent_status_changed"
        ]
        self.assertEqual(
            sorted(s["pane_id"] for s in status_subs), ["w1:p1", "w1:p2"]
        )


class EventHandlingTests(DaemonTestCase):
    def setUp(self):
        super().setUp()
        self.server.set_handler(
            "pane.list", lambda params: {"panes": [pane_info("w1:p1", status="idle")]}
        )
        self.d.bootstrap()

    def test_status_change_updates_cached_status(self):
        self.d.handle_event(
            {
                "event": "pane.agent_status_changed",
                "data": {"pane_id": "w1:p1", "agent_status": "working"},
            }
        )
        self.assertEqual(self.d.panes["w1:p1"].status, "working")

    def test_unchanged_status_event_is_ignored(self):
        # Our own title reports re-fire pane.agent_status_changed as a
        # presentation change; the payload's agent_status is unchanged, so
        # this must not be treated as a transition.
        record = self.d.panes["w1:p1"]
        record.status = "working"
        self.d.handle_event(
            {
                "event": "pane.agent_status_changed",
                "data": {"pane_id": "w1:p1", "agent_status": "working"},
            }
        )
        self.assertEqual(self.d.panes["w1:p1"].status, "working")

    def test_pane_created_adds_to_cache_and_marks_topology_dirty(self):
        self.d.handle_event(
            {
                "event": "pane.created",
                "data": {"pane": pane_info("w1:p2", status="idle")},
            }
        )
        self.assertIn("w1:p2", self.d.panes)
        self.assertTrue(self.d._topology_dirty())

    def test_pane_closed_removes_from_cache(self):
        self.d.handle_event(
            {"event": "pane.closed", "data": {"pane_id": "w1:p1"}}
        )
        self.assertNotIn("w1:p1", self.d.panes)

    def test_unknown_event_is_ignored_without_error(self):
        self.d.handle_event({"event": "layout.updated", "data": {}})  # must not raise


class TickReportingTests(DaemonTestCase):
    def setUp(self):
        super().setUp()
        self.server.set_handler("pane.report_metadata", lambda params: {})
        self.server.set_handler("tab.get", lambda params: {"tab": {"label": "my-tab"}})
        self.server.set_handler("tab.rename", lambda params: {})

    def test_working_pane_gets_animated_title_with_ttl_seq_and_agent_guard(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {
                "panes": [pane_info("w1:p1", status="working", agent="claude", title="refactor auth")]
            },
        )
        self.d.bootstrap()
        self.d.tick(1)

        calls = self.report_calls()
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call["pane_id"], "w1:p1")
        self.assertEqual(call["source"], "agent-pulse")
        self.assertEqual(call["agent"], "claude")
        self.assertIn("refactor auth", call["title"])
        self.assertEqual(call["ttl_ms"], daemon.frame_ttl_ms(4))
        first_seq = call["seq"]
        self.assertGreater(first_seq, 1_000_000_000_000)  # wall-clock ms, not a small counter

        self.d.tick(2)
        self.assertGreater(self.report_calls()[-1]["seq"], first_seq)

    def test_blocked_pane_gets_static_label(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", status="blocked")]},
        )
        self.d.bootstrap()
        self.d.tick(1)
        call = self.report_calls()[-1]
        self.assertEqual(call["title"], "✋ needs you")

    def test_idle_pane_after_working_gets_title_cleared(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", status="working")]},
        )
        self.d.bootstrap()
        self.d.tick(1)
        self.assertTrue(self.d.panes["w1:p1"].reporting)

        self.d.panes["w1:p1"].status = "idle"
        self.d.tick(2)
        call = self.report_calls()[-1]
        self.assertEqual(call["pane_id"], "w1:p1")
        self.assertTrue(call.get("clear_title"))
        self.assertFalse(self.d.panes["w1:p1"].reporting)

    def test_idle_pane_never_reported_generates_no_calls(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", status="idle")]},
        )
        self.d.bootstrap()
        self.d.tick(1)
        self.assertEqual(self.report_calls(), [])


class TabRenameTests(DaemonTestCase):
    def setUp(self):
        super().setUp()
        self.server.set_handler("pane.report_metadata", lambda params: {})
        self.tab_get_calls = []

        def tab_get(params):
            self.tab_get_calls.append(params)
            return {"tab": {"label": "my-tab"}}

        self.server.set_handler("tab.get", tab_get)
        self.server.set_handler("tab.rename", lambda params: {})

    def test_rename_happens_once_when_tab_becomes_active(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="working")]},
        )
        self.d.bootstrap()
        self.d.tick(1)
        self.d.tick(2)
        self.d.tick(3)

        renames = self.rename_calls()
        self.assertEqual(len(renames), 1)
        self.assertEqual(renames[0]["label"], "◐ my-tab")
        # tab.get (to learn the original label) happens only once, not per tick.
        self.assertEqual(len(self.tab_get_calls), 1)

    def test_rename_updates_icon_when_aggregate_status_changes(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="working")]},
        )
        self.d.bootstrap()
        self.d.tick(1)

        self.d.panes["w1:p1"].status = "blocked"
        self.d.tick(2)

        renames = self.rename_calls()
        self.assertEqual(len(renames), 2)
        self.assertEqual(renames[0]["label"], "◐ my-tab")
        self.assertEqual(renames[1]["label"], "✋ my-tab")

    def test_restore_when_tab_returns_to_idle(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="working")]},
        )
        self.d.bootstrap()
        self.d.tick(1)

        self.d.panes["w1:p1"].status = "idle"
        self.d.tick(2)

        renames = self.rename_calls()
        self.assertEqual(renames[-1]["label"], "my-tab")
        self.assertIsNone(self.tab_cache.get("t1"))

    def test_restart_after_crash_never_stacks_icons(self):
        # Simulate a previous run that renamed the tab but crashed before
        # restoring it: the server-side label is already prefixed, and our
        # cache file is gone (as if the crash happened before caching).
        self.server.set_handler(
            "tab.get", lambda params: {"tab": {"label": "◐ my-tab"}}
        )
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="blocked")]},
        )
        self.d.bootstrap()
        self.d.tick(1)

        renames = self.rename_calls()
        self.assertEqual(renames[-1]["label"], "✋ my-tab")


class SummaryFileTests(DaemonTestCase):
    def setUp(self):
        super().setUp()
        self.server.set_handler("pane.report_metadata", lambda params: {})
        self.server.set_handler("tab.get", lambda params: {"tab": {"label": "my-tab"}})
        self.server.set_handler("tab.rename", lambda params: {})

    def test_summary_file_reflects_working_and_blocked_counts(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {
                "panes": [
                    pane_info("w1:p1", tab_id="t1", status="working"),
                    pane_info("w1:p2", tab_id="t2", status="blocked"),
                ]
            },
        )
        self.d.bootstrap()
        self.d.tick(1)

        summary_path = os.path.join(self.state_dir, "summary.txt")
        with open(summary_path) as fh:
            content = fh.read()
        self.assertEqual(content, "◐ 1 · ✋ 1\n")

    def test_summary_file_empty_when_nothing_active(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", status="idle")]},
        )
        self.d.bootstrap()
        self.d.tick(1)

        summary_path = os.path.join(self.state_dir, "summary.txt")
        with open(summary_path) as fh:
            content = fh.read()
        self.assertEqual(content, "\n")


class RunLoopTests(DaemonTestCase):
    def setUp(self):
        super().setUp()
        self.server.set_handler("pane.report_metadata", lambda params: {})
        self.server.set_handler("tab.get", lambda params: {"tab": {"label": "my-tab"}})
        self.server.set_handler("tab.rename", lambda params: {})
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="working")]},
        )

    def _run_in_background(self):
        import threading

        thread = threading.Thread(target=self.d.run)
        thread.start()
        self.addCleanup(lambda: thread.join(timeout=2))
        return thread

    def test_run_reacts_to_pushed_status_change_then_shuts_down_cleanly_on_eof(self):
        thread = self._run_in_background()
        self.assertTrue(self.server.wait_for_subscription(1))

        self.server.push_event(
            {
                "event": "pane.agent_status_changed",
                "data": {"pane_id": "w1:p1", "agent_status": "blocked"},
            }
        )
        # Real wall-clock pause (fps=4 -> one frame is 0.25s): give the
        # running loop a chance to actually tick and report before EOF,
        # since the socket's own recv() timeouts are real wall-clock time
        # regardless of any injected clock.
        import time as _time

        _time.sleep(0.4)
        self.server.close_subscription()
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

        self.assertEqual(self.d.panes["w1:p1"].status, "blocked")
        calls = self.report_calls()
        self.assertTrue(any(c.get("title") == "✋ needs you" for c in calls))
        # Shutdown clears whatever title it last owned and restores the tab.
        self.assertTrue(calls[-1].get("clear_title"))
        renames = self.rename_calls()
        self.assertEqual(renames[-1]["label"], "my-tab")
        self.assertIsNone(self.tab_cache.get("t1"))

    def test_run_reconnects_when_a_new_pane_appears(self):
        thread = self._run_in_background()
        self.assertTrue(self.server.wait_for_subscription(1))

        self.server.push_event(
            {
                "event": "pane.created",
                "data": {"pane": pane_info("w1:p2", tab_id="t1", status="idle")},
            }
        )
        self.assertTrue(self.server.wait_for_subscription(2))
        self.server.close_subscription(connection=-1)
        thread.join(timeout=2)
        self.assertFalse(thread.is_alive())

        subscribe_calls = [
            params
            for method, params in self.server.received_requests
            if method == "events.subscribe"
        ]
        self.assertEqual(len(subscribe_calls), 2)
        last_pane_ids = sorted(
            s["pane_id"]
            for s in subscribe_calls[-1]["subscriptions"]
            if s["type"] == "pane.agent_status_changed"
        )
        self.assertEqual(last_pane_ids, ["w1:p1", "w1:p2"])


class RealResponseContractTests(DaemonTestCase):
    """Uses REAL captured herdr response envelopes (tests/fixtures/), not
    hand-written shapes, so an unwrap mistake like reading a top-level key
    on a response that actually wraps it under "tab"/"pane" gets caught."""

    def test_task_text_refresh_unwraps_real_pane_get_response(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w7:p21", tab_id="w7:t21", status="working")]},
        )
        self.server.set_handler(
            "pane.get", lambda params: load_fixture_result("pane_get_response.json")
        )
        self.d.bootstrap()

        self.d._refresh_task_text()

        self.assertEqual(self.d.panes["w7:p21"].task_text, "Refactor parser")

    def test_tab_rename_unwraps_real_tab_get_response_and_caches_real_label(self):
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w7:p3Z", tab_id="w7:t3Z", status="working")]},
        )
        self.server.set_handler(
            "tab.get", lambda params: load_fixture_result("tab_get_response.json")
        )
        self.server.set_handler("tab.rename", lambda params: {})
        self.d.bootstrap()

        renamed = self.d._rename_tab("w7:t3Z", "working")

        self.assertTrue(renamed)
        self.assertEqual(self.tab_cache.get("w7:t3Z"), "api-server")
        self.assertEqual(self.rename_calls()[-1]["label"], "◐ api-server")

    def test_tab_rename_skips_and_logs_when_real_label_is_empty(self):
        self.server.set_handler(
            "tab.get",
            lambda params: load_fixture_result("tab_get_response_empty_label.json"),
        )
        self.server.set_handler("tab.rename", lambda params: {})

        renamed = self.d._rename_tab("w7:tEmpty", "working")

        self.assertFalse(renamed)
        self.assertIsNone(self.tab_cache.get("w7:tEmpty"))
        self.assertEqual(self.rename_calls(), [])
        self.assertTrue(any("w7:tEmpty" in line for line in self.log_lines))


class RequestFailureResilienceTests(DaemonTestCase):
    """Before this fix, an error response from pane.report_metadata/tab.get/
    tab.rename propagated as an uncaught HerdrError out of tick(), aborting
    the rest of that tick (and everything after it in the caller) silently
    -- daemon.log was never even created. These reproduce that gap."""

    def setUp(self):
        super().setUp()
        self.server.set_handler("tab.get", lambda params: {"tab": {"label": "my-tab"}})
        self.server.set_handler("tab.rename", lambda params: {})

    def test_report_metadata_failure_for_one_pane_does_not_abort_the_tick(self):
        def report_metadata(params):
            if params["pane_id"] == "w1:p1":
                return {"__error__": {"code": "invalid_params", "message": "boom"}}
            return {}

        self.server.set_handler("pane.report_metadata", report_metadata)
        self.server.set_handler(
            "pane.list",
            lambda params: {
                "panes": [
                    pane_info("w1:p1", tab_id="t1", status="working"),
                    pane_info("w1:p2", tab_id="t2", status="working"),
                ]
            },
        )
        self.d.bootstrap()

        self.d.tick(1)  # must not raise

        reported_panes = {c["pane_id"] for c in self.report_calls()}
        self.assertIn("w1:p2", reported_panes)
        self.assertTrue(
            any("pane.report_metadata" in line and "w1:p1" in line for line in self.log_lines)
        )

    def test_tick_after_a_failed_tick_still_reports(self):
        calls = {"n": 0}

        def report_metadata(params):
            calls["n"] += 1
            if calls["n"] == 1:
                return {"__error__": {"code": "invalid_params", "message": "boom"}}
            return {}

        self.server.set_handler("pane.report_metadata", report_metadata)
        self.server.set_handler(
            "pane.list",
            lambda params: {"panes": [pane_info("w1:p1", tab_id="t1", status="working")]},
        )
        self.d.bootstrap()

        self.d.tick(1)  # must not raise, even though this attempt errors
        self.d.tick(2)

        # Both ticks attempted a report (tick 1's failed server-side); what
        # matters is tick 2 was never skipped because tick 1 raised.
        self.assertEqual(calls["n"], 2)
        seqs = [c["seq"] for c in self.report_calls()]
        self.assertGreater(seqs[1], seqs[0])


class TabIconsDisabledShutdownTests(DaemonTestCase):
    def test_shutdown_does_not_touch_tabs_when_tab_icons_disabled(self):
        self.cfg.tab_icons = False
        self.tab_cache.set("t1", "my-tab")  # pre-existing cache from a previous run
        self.server.set_handler(
            "pane.list", lambda params: {"panes": [pane_info("w1:p1", status="idle")]}
        )
        self.server.set_handler("pane.report_metadata", lambda params: {})
        self.d.bootstrap()

        self.d._shutdown()

        self.assertEqual(self.rename_calls(), [])
        self.assertEqual(self.tab_cache.get("t1"), "my-tab")  # untouched


class SeqSurvivesRestartTests(DaemonTestCase):
    """Live bug (found after T3b's unwrap fix, still with no error logged):
    herdr silently drops a pane.report_metadata whose `seq` is not strictly
    greater than the last one it accepted FOR THAT PANE+SOURCE -- and that
    high-water mark lives on the pane, not on our daemon process (verified
    in herdr v0.9.1 src/metadata_tokens.rs::sequence_is_fresh and
    src/terminal/metadata.rs::accept_metadata_report). A per-process
    counter that restarts at 0/1 on every daemon restart is therefore
    silently rejected forever after the first restart against a long-lived
    pane -- "request succeeded, title never changes, no error anywhere."
    """

    def test_seq_does_not_reset_to_a_low_number_across_daemon_restarts(self):
        first = daemon.Daemon(
            self.herdr_client, self.cfg, self.tab_cache, self.log_lines.append, self.state_dir
        )
        second = daemon.Daemon(
            self.herdr_client, self.cfg, self.tab_cache, self.log_lines.append, self.state_dir
        )
        # Wall-clock-scale, not a small per-instance counter starting over.
        self.assertGreater(first._next_seq(), 1_000_000_000_000)
        self.assertGreater(second._next_seq(), 1_000_000_000_000)

    def test_next_seq_is_strictly_increasing_within_one_instance(self):
        seqs = [self.d._next_seq() for _ in range(5)]
        self.assertEqual(seqs, sorted(set(seqs)))
        self.assertEqual(len(seqs), len(set(seqs)))


class NeverCacheOrRestoreEmptyLabelTests(DaemonTestCase):
    def test_restore_skips_when_cached_original_is_empty_string(self):
        # Defends against a corrupted cache file (e.g. from before this fix)
        # rather than only the code path that would create one now.
        self.tab_cache._labels["t1"] = ""
        self.tab_cache._save()

        restored = self.d._restore_tab_label("t1")

        self.assertFalse(restored)
        self.assertEqual(self.rename_calls(), [])


if __name__ == "__main__":
    unittest.main()
