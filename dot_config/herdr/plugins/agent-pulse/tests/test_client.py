import os
import tempfile
import unittest

from agent_pulse import client
from tests.fake_server import FakeHerdrServer


class HerdrClientTestCase(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="apsock-", dir="/tmp")
        self.socket_path = os.path.join(self.tmpdir, "herdr.sock")
        self.server = FakeHerdrServer(self.socket_path)
        self.client = client.HerdrClient(path=self.socket_path, timeout=2.0)

    def tearDown(self):
        self.server.stop()
        try:
            os.rmdir(self.tmpdir)
        except OSError:
            pass


class RequestResponseTests(HerdrClientTestCase):
    def test_request_returns_result(self):
        self.server.set_handler(
            "pane.list", lambda params: {"panes": [{"pane_id": "w1:p1"}]}
        )
        result = self.client.request("pane.list", {"workspace_id": None})
        self.assertEqual(result, {"panes": [{"pane_id": "w1:p1"}]})

    def test_request_sends_method_and_params(self):
        self.server.set_handler("pane.get", lambda params: {"pane": params})
        result = self.client.request("pane.get", {"pane_id": "w1:p1"})
        self.assertEqual(result, {"pane": {"pane_id": "w1:p1"}})
        self.assertEqual(
            self.server.received_requests[-1],
            ("pane.get", {"pane_id": "w1:p1"}),
        )

    def test_request_raises_on_error_response(self):
        self.server.set_handler(
            "pane.get",
            lambda params: {"__error__": {"code": "not_found", "message": "no such pane"}},
        )
        with self.assertRaises(client.HerdrError) as ctx:
            self.client.request("pane.get", {"pane_id": "missing"})
        self.assertEqual(ctx.exception.code, "not_found")

    def test_request_uses_one_connection_per_call(self):
        self.server.set_handler("ping", lambda params: {})
        self.client.request("ping", {})
        self.client.request("ping", {})
        self.assertEqual(len(self.server.received_requests), 2)


class SubscriptionTests(HerdrClientTestCase):
    def test_subscribe_sends_subscriptions_and_acks(self):
        subs = [{"type": "pane.created"}]
        subscription = self.client.subscribe(subs)
        self.assertEqual(
            self.server.received_requests[-1][0], "events.subscribe"
        )
        self.assertEqual(
            self.server.received_requests[-1][1]["subscriptions"], subs
        )
        subscription.close()

    def test_poll_returns_pushed_events_in_order(self):
        subscription = self.client.subscribe([{"type": "pane.created"}])
        self.server.push_event({"event": "pane.created", "data": {"pane_id": "w1:p1"}})
        self.server.push_event({"event": "pane.created", "data": {"pane_id": "w1:p2"}})

        first = subscription.poll(timeout=2.0)
        second = subscription.poll(timeout=2.0)
        self.assertEqual(first["data"]["pane_id"], "w1:p1")
        self.assertEqual(second["data"]["pane_id"], "w1:p2")
        subscription.close()

    def test_poll_returns_none_on_timeout_with_no_events(self):
        subscription = self.client.subscribe([{"type": "pane.created"}])
        result = subscription.poll(timeout=0.2)
        self.assertIsNone(result)
        subscription.close()

    def test_poll_raises_subscription_closed_on_server_eof(self):
        subscription = self.client.subscribe([{"type": "pane.created"}])
        self.server.close_subscription()
        with self.assertRaises(client.SubscriptionClosed):
            subscription.poll(timeout=2.0)


if __name__ == "__main__":
    unittest.main()
