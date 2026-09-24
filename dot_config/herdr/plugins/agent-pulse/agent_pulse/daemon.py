"""agent-pulse daemon.

Watches herdr pane agent_status over the socket API and reports an animated
pane-border title, a tab-label state icon, and a tab-bar-right summary file.
Run as `python3 -m agent_pulse.daemon`; normally launched by `bin/ensure-daemon`.

Platform constraint (verified against herdr v0.9.1 source,
src/api/schema/events.rs + src/api/subscriptions.rs): the
`pane.agent_status_changed` subscription requires a `pane_id` -- there is no
wildcard "every pane" filter, and a connection's subscription set is fixed
for its lifetime (src/api/server.rs::stream_subscriptions builds it once and
never re-reads the connection). So this daemon subscribes to the pane_ids it
already knows about, plus the unfiltered `pane.created`/`pane.closed`/
`pane.exited` lifecycle events (which need no pane_id and always arrive
live); when a new pane appears, its PaneInfo is already in the event's own
payload, but it has no per-pane subscription yet, so the daemon reconnects
`events.subscribe` with the updated pane set the next time it notices the
mismatch. An unexpected close of that connection means the herdr server
itself went away, not that we should retry -- the daemon shuts down cleanly
instead.
"""

import errno
import json
import os
import signal
import sys
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - herdr's plugin platforms are macOS/Linux only
    fcntl = None

from agent_pulse import client as client_module
from agent_pulse import config as config_module
from agent_pulse import core

SOURCE = "agent-pulse"
PID_FILE_NAME = "daemon.pid"
TAB_LABELS_FILE_NAME = "tab_labels.json"
SUMMARY_FILE_NAME = "summary.txt"
LOG_FILE_NAME = "daemon.log"
LOG_MAX_BYTES = 256 * 1024

TASK_TEXT_REFRESH_INTERVAL = 1.0  # seconds; how often working panes' task text is re-read
MAIN_LOOP_MAX_POLL = 0.25  # seconds; upper bound so we never block past a due schedule


def frame_interval_seconds(fps):
    return 1.0 / max(1, fps)


def frame_ttl_ms(fps):
    """TTL so a dead daemon self-heals within about 3 missed frames, floored at 1s."""
    interval_ms = 1000.0 / max(1, fps)
    return int(max(1000, 3 * interval_ms))


def build_subscriptions(pane_ids):
    """Lifecycle events (no pane_id needed) plus one status filter per known pane."""
    subscriptions = [
        {"type": "pane.created"},
        {"type": "pane.closed"},
        {"type": "pane.exited"},
    ]
    for pane_id in pane_ids:
        subscriptions.append(
            {"type": "pane.agent_status_changed", "pane_id": pane_id}
        )
    return subscriptions


# ---- Singleton lock ---------------------------------------------------------


def _ensure_dir(path):
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise


class SingletonLock(object):
    def __init__(self, path, handle):
        self._path = path
        self._handle = handle

    def release(self):
        try:
            fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        except OSError:
            pass
        try:
            os.remove(self._path)
        except OSError:
            pass
        self._handle.close()


def acquire_singleton_lock(state_directory):
    """Return a held SingletonLock, or None if another daemon already holds it."""
    _ensure_dir(state_directory)
    path = os.path.join(state_directory, PID_FILE_NAME)
    handle = open(path, "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return SingletonLock(path, handle)


# ---- Tab label cache ---------------------------------------------------------


class TabLabelCache(object):
    """Persists {tab_id: original_label} so a crash/restart never stacks icons."""

    def __init__(self, state_directory):
        self._path = os.path.join(state_directory, TAB_LABELS_FILE_NAME)
        self._labels = self._load()

    def _load(self):
        try:
            with open(self._path, "r") as fh:
                data = json.load(fh)
        except (IOError, OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _save(self):
        tmp_path = self._path + ".tmp"
        with open(tmp_path, "w") as fh:
            json.dump(self._labels, fh)
        os.replace(tmp_path, self._path)

    def get(self, tab_id):
        return self._labels.get(tab_id)

    def set(self, tab_id, original_label):
        self._labels[tab_id] = original_label
        self._save()

    def pop(self, tab_id):
        if tab_id in self._labels:
            del self._labels[tab_id]
            self._save()

    def items(self):
        return list(self._labels.items())


# ---- Pane bookkeeping ---------------------------------------------------------


class PaneRecord(object):
    __slots__ = ("pane_id", "tab_id", "status", "agent", "task_text", "reporting")

    def __init__(self, pane_id, tab_id, status, agent=None, task_text=None):
        self.pane_id = pane_id
        self.tab_id = tab_id
        self.status = status
        self.agent = agent
        self.task_text = task_text
        self.reporting = False  # True once we've reported a title this pane still owns

    @classmethod
    def from_pane_info(cls, pane_info):
        return cls(
            pane_id=pane_info["pane_id"],
            tab_id=pane_info.get("tab_id"),
            status=pane_info.get("agent_status", "unknown"),
            agent=pane_info.get("agent"),
            task_text=pane_info.get("terminal_title_stripped"),
        )


# ---- Daemon ---------------------------------------------------------


class Daemon(object):
    def __init__(
        self,
        herdr_client,
        cfg,
        tab_cache,
        log,
        state_directory,
        now=time.monotonic,
        wall_clock=time.time,
    ):
        self.client = herdr_client
        self.cfg = cfg
        self.tab_cache = tab_cache
        self.log = log
        self.state_directory = state_directory
        self._now = now
        self._wall_clock = wall_clock

        self.panes = {}  # pane_id -> PaneRecord
        self.tab_aggregate = {}  # tab_id -> last reported aggregate status
        self._last_seq = 0
        self._running = True
        self._subscription = None
        self._subscribed_pane_ids = set()
        self._last_summary = None
        self.summary_path = os.path.join(state_directory, SUMMARY_FILE_NAME)

    # -- lifecycle --

    def stop(self, *_args):
        self._running = False

    def bootstrap(self):
        result = self.client.request("pane.list", {})
        for info in result.get("panes", []):
            self.panes[info["pane_id"]] = PaneRecord.from_pane_info(info)
        self._resubscribe()

    def run(self):
        """The main loop. Signal handlers are the caller's job (see main()):

        registering them here would break running this loop from a thread
        that is not the process's main thread, e.g. in tests.
        """
        self.log(
            "started pid={} theme={} fps={} tab_icons={}".format(
                os.getpid(), self.cfg.theme, self.cfg.fps, self.cfg.tab_icons
            )
        )
        self.bootstrap()

        frame_interval = frame_interval_seconds(self.cfg.fps)
        tick_index = 0
        next_frame_at = self._now()
        next_task_refresh_at = self._now()

        try:
            while self._running:
                timeout = min(
                    MAIN_LOOP_MAX_POLL,
                    max(0.0, next_frame_at - self._now()),
                    max(0.0, next_task_refresh_at - self._now()),
                )
                try:
                    event = self._subscription.poll(timeout)
                except client_module.SubscriptionClosed:
                    self.log("subscription closed by herdr server; shutting down")
                    break

                if event is not None:
                    self.handle_event(event)

                now = self._now()
                if now >= next_frame_at:
                    tick_index += 1
                    try:
                        self.tick(tick_index)
                    except Exception as err:  # keep the loop alive; log and move on
                        self.log("tick {} raised {}: {}".format(tick_index, type(err).__name__, err))
                    next_frame_at += frame_interval
                if now >= next_task_refresh_at:
                    try:
                        self._refresh_task_text()
                    except Exception as err:
                        self.log("task text refresh raised {}: {}".format(type(err).__name__, err))
                    next_task_refresh_at += TASK_TEXT_REFRESH_INTERVAL

                if self._topology_dirty():
                    self._resubscribe()
        finally:
            self._shutdown()

    def _shutdown(self):
        for record in list(self.panes.values()):
            if record.reporting:
                self._clear_title(record)
                record.reporting = False
        if self.cfg.tab_icons:
            for tab_id, _original in self.tab_cache.items():
                self._restore_tab_label(tab_id)
        if self._subscription is not None:
            self._subscription.close()

    # -- request helper: log and swallow instead of propagating --

    def _try_request(self, method, params):
        try:
            return self.client.request(method, params)
        except (client_module.HerdrError, OSError) as err:
            self.log("request failed: method={} params={} error={}".format(method, params, err))
            return None

    def _next_seq(self):
        """A `seq` for pane.report_metadata that is safe across restarts.

        herdr silently drops a report whose seq is not strictly greater
        than the last one it accepted for that (pane, source) pair, and
        that high-water mark lives on the pane, not on our process
        (verified in herdr v0.9.1 src/metadata_tokens.rs::sequence_is_fresh
        and src/terminal/metadata.rs::accept_metadata_report -- the report
        is accepted by the socket API but ignored by the pane state, with
        no error). A per-process counter starting at 0/1 on every restart
        collides with that persistent high-water mark and gets silently
        ignored forever. Wall-clock milliseconds keep climbing across
        restarts; the local counter only kicks in to guarantee strict
        monotonicity for two calls within the same millisecond.
        """
        candidate = int(self._wall_clock() * 1000)
        if candidate <= self._last_seq:
            candidate = self._last_seq + 1
        self._last_seq = candidate
        return candidate

    # -- subscription management --

    def _resubscribe(self):
        if self._subscription is not None:
            self._subscription.close()
        pane_ids = list(self.panes.keys())
        self._subscription = self.client.subscribe(build_subscriptions(pane_ids))
        self._subscribed_pane_ids = set(pane_ids)

    def _topology_dirty(self):
        return set(self.panes.keys()) != self._subscribed_pane_ids

    # -- event handling --

    def handle_event(self, envelope):
        event = envelope.get("event")
        data = envelope.get("data", {})
        if event == "pane.agent_status_changed":
            self._handle_status_changed(data)
        elif event == "pane.created":
            self._handle_pane_created(data)
        elif event in ("pane.closed", "pane.exited"):
            self._handle_pane_removed(data)
        # Other lifecycle events are not subscribed to; ignore defensively.

    def _handle_status_changed(self, data):
        record = self.panes.get(data.get("pane_id"))
        if record is None:
            return
        new_status = data.get("agent_status", record.status)
        if new_status == record.status:
            # Our own title reports re-fire this event as a presentation
            # change; only a real status transition matters here.
            return
        record.status = new_status
        if "agent" in data:
            record.agent = data["agent"]

    def _handle_pane_created(self, data):
        pane_info = data.get("pane")
        if not pane_info or pane_info["pane_id"] in self.panes:
            return
        self.panes[pane_info["pane_id"]] = PaneRecord.from_pane_info(pane_info)

    def _handle_pane_removed(self, data):
        self.panes.pop(data.get("pane_id"), None)

    # -- per-tick reporting --

    def tick(self, tick_index):
        self._report_working_and_blocked(tick_index)
        self._update_tab_labels()
        self._write_summary()

    def _report_working_and_blocked(self, tick_index):
        for record in self.panes.values():
            if record.status == "working":
                title = core.border_title(
                    self.cfg.theme, "working", tick_index, record.task_text
                )
                self._report_title(record, title, frame_ttl_ms(self.cfg.fps))
                record.reporting = True
            elif record.status == "blocked":
                title = core.border_title(
                    self.cfg.theme, "blocked", tick_index, record.task_text
                )
                self._report_title(record, title, frame_ttl_ms(self.cfg.fps))
                record.reporting = True
            elif record.reporting:
                self._clear_title(record)
                record.reporting = False

    def _report_title(self, record, title, ttl_ms):
        self._try_request(
            "pane.report_metadata",
            {
                "pane_id": record.pane_id,
                "source": SOURCE,
                "agent": record.agent,
                "title": title,
                "ttl_ms": ttl_ms,
                "seq": self._next_seq(),
            },
        )

    def _clear_title(self, record):
        self._try_request(
            "pane.report_metadata",
            {
                "pane_id": record.pane_id,
                "source": SOURCE,
                "clear_title": True,
                "seq": self._next_seq(),
            },
        )

    def _refresh_task_text(self):
        for record in self.panes.values():
            if record.status != "working":
                continue
            response = self._try_request("pane.get", {"pane_id": record.pane_id})
            if response is None:
                continue
            # Real response: {"pane": {...}, "type": "pane_info"} -- the
            # pane fields are wrapped, not top-level (verified against a
            # live `herdr pane get` capture; see tests/fixtures).
            record.task_text = response.get("pane", {}).get("terminal_title_stripped")

    # -- tab labels --

    def _update_tab_labels(self):
        if not self.cfg.tab_icons:
            return

        statuses_by_tab = {}
        for record in self.panes.values():
            if record.tab_id:
                statuses_by_tab.setdefault(record.tab_id, []).append(record.status)

        for tab_id, statuses in statuses_by_tab.items():
            aggregate = core.aggregate_tab_status(statuses)
            if aggregate == self.tab_aggregate.get(tab_id, "idle"):
                continue
            # Only commit the new aggregate once the action actually
            # succeeds, so a failed/skipped rename is retried next tick
            # instead of being silently forgotten.
            if aggregate == "idle":
                if self._restore_tab_label(tab_id):
                    self.tab_aggregate[tab_id] = aggregate
            elif self._rename_tab(tab_id, aggregate):
                self.tab_aggregate[tab_id] = aggregate

        # A tab whose last pane just disappeared: restore if we'd renamed it.
        for tab_id in [t for t in self.tab_aggregate if t not in statuses_by_tab]:
            if self.tab_aggregate[tab_id] != "idle":
                if self._restore_tab_label(tab_id):
                    del self.tab_aggregate[tab_id]
            else:
                del self.tab_aggregate[tab_id]

    def _rename_tab(self, tab_id, aggregate):
        """Return True on a successful rename, False if skipped/failed."""
        original = self.tab_cache.get(tab_id)
        if original is None:
            response = self._try_request("tab.get", {"tab_id": tab_id})
            if response is None:
                return False
            # Real response: {"tab": {...}, "type": "tab_info"} -- the tab
            # fields are wrapped, not top-level (verified against a live
            # `herdr tab get` capture; see tests/fixtures). Reading a
            # top-level "label" here silently returned "" and cached that
            # empty string as the "original" label, which is exactly what
            # destroyed 6 real tab names in the first live run.
            label = response.get("tab", {}).get("label")
            original = core.strip_known_prefix(label) if label else ""
            if not original:
                self.log(
                    "skip rename: tab {} has no safely readable original label "
                    "(got {!r}); leaving it untouched".format(tab_id, label)
                )
                return False
            self.tab_cache.set(tab_id, original)
        icon = core.tab_icon(self.cfg.theme, aggregate)
        if icon is None:
            return False
        result = self._try_request(
            "tab.rename",
            {"tab_id": tab_id, "label": core.compose_tab_label(icon, original)},
        )
        return result is not None

    def _restore_tab_label(self, tab_id):
        """Return True on a successful restore, or when there was nothing to
        restore; False when a restore was needed but skipped or failed."""
        original = self.tab_cache.get(tab_id)
        if original is None:
            return True
        if not original:
            # Never restore an empty cached label: that would overwrite
            # whatever the tab is currently called with blank text. This
            # cache entry is corrupt (e.g. from before this fix); leave the
            # tab alone rather than guess.
            self.log(
                "skip restore: tab {} has an empty cached original label; "
                "leaving it untouched".format(tab_id)
            )
            return False
        result = self._try_request("tab.rename", {"tab_id": tab_id, "label": original})
        if result is None:
            return False
        self.tab_cache.pop(tab_id)
        return True

    # -- summary file --

    def _write_summary(self):
        text = core.summary(self.cfg.theme, [r.status for r in self.panes.values()]) + "\n"
        if text == self._last_summary:
            return
        self._last_summary = text
        tmp_path = self.summary_path + ".tmp"
        with open(tmp_path, "w") as fh:
            fh.write(text)
        os.replace(tmp_path, self.summary_path)


# ---- entrypoint ---------------------------------------------------------


def _file_logger(state_directory):
    path = os.path.join(state_directory, LOG_FILE_NAME)

    def log(message):
        try:
            if os.path.exists(path) and os.path.getsize(path) > LOG_MAX_BYTES:
                os.remove(path)
            with open(path, "a") as fh:
                fh.write("{} {}\n".format(time.strftime("%Y-%m-%dT%H:%M:%S"), message))
        except OSError:
            pass

    return log


def main():
    state_directory = config_module.state_dir()
    _ensure_dir(state_directory)

    lock = acquire_singleton_lock(state_directory)
    if lock is None:
        return 0  # another daemon instance already holds it; hooks fire concurrently

    log = _file_logger(state_directory)
    try:
        cfg = config_module.load()
        tab_cache = TabLabelCache(state_directory)
        herdr_client = client_module.HerdrClient()
        daemon = Daemon(herdr_client, cfg, tab_cache, log, state_directory)
        signal.signal(signal.SIGTERM, daemon.stop)
        signal.signal(signal.SIGINT, daemon.stop)
        daemon.run()
    except Exception as err:  # pragma: no cover - last-resort logging
        log("daemon crashed: {}".format(err))
    finally:
        lock.release()
    return 0


if __name__ == "__main__":
    sys.exit(main())
