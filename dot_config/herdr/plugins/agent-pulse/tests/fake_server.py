"""A minimal fake herdr NDJSON socket server for tests.

This is not a herdr reimplementation. It gives tests a real Unix socket that
speaks just enough of the wire protocol (one request per connection, plus a
long-lived events.subscribe stream) to exercise agent_pulse.client and
agent_pulse.daemon without a live herdr server.
"""

import json
import os
import queue
import socket
import threading

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def load_fixture_result(name):
    """Return the `result` object of a captured (or documented-constructed)
    herdr response envelope from tests/fixtures/<name>, so a test handler can
    serve the REAL wrapped shape instead of a hand-written guess."""
    with open(os.path.join(FIXTURES_DIR, name)) as fh:
        envelope = json.load(fh)
    return envelope["result"]


class FakeHerdrServer:
    def __init__(self, socket_path):
        self.socket_path = socket_path
        if os.path.exists(socket_path):
            os.unlink(socket_path)
        self._sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._sock.bind(socket_path)
        self._sock.listen(8)
        self._sock.settimeout(0.2)
        self._handlers = {}
        self.received_requests = []
        self._sub_connections = []  # one Queue per events.subscribe connection, in accept order
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def set_handler(self, method, fn):
        """fn(params) -> result dict, or {"__error__": {"code":.., "message":..}}"""
        self._handlers[method] = fn

    def wait_for_subscription(self, count, timeout=2.0):
        """Block until at least `count` events.subscribe connections have been accepted."""
        import time as _time

        deadline = _time.time() + timeout
        while _time.time() < deadline:
            with self._lock:
                if len(self._sub_connections) >= count:
                    return True
            _time.sleep(0.01)
        return False

    def push_event(self, event, connection=-1):
        with self._lock:
            q = self._sub_connections[connection]
        q.put(("event", event))

    def close_subscription(self, connection=-1):
        with self._lock:
            q = self._sub_connections[connection]
        q.put(("close", None))

    def stop(self):
        self._stop.set()
        with self._lock:
            queues = list(self._sub_connections)
        for q in queues:
            q.put(("close", None))
        self._thread.join(timeout=2)
        try:
            self._sock.close()
        finally:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)

    def _serve(self):
        while not self._stop.is_set():
            try:
                conn, _ = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn):
        with conn:
            conn.settimeout(2)
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(65536)
                if not chunk:
                    return
                buf += chunk
            line, _, _ = buf.partition(b"\n")
            request = json.loads(line.decode("utf-8"))
            method = request["method"]
            params = request.get("params", {})
            with self._lock:
                self.received_requests.append((method, params))

            if method == "events.subscribe":
                self._serve_subscription(conn, request)
                return

            handler = self._handlers.get(method)
            if handler is None:
                response = {"id": request["id"], "result": {}}
            else:
                result = handler(params)
                if isinstance(result, dict) and "__error__" in result:
                    response = {"id": request["id"], "error": result["__error__"]}
                else:
                    response = {"id": request["id"], "result": result}
            conn.sendall((json.dumps(response) + "\n").encode("utf-8"))

    def _serve_subscription(self, conn, request):
        q = queue.Queue()
        with self._lock:
            self._sub_connections.append(q)
        ack = {"id": request["id"], "result": {}}
        conn.sendall((json.dumps(ack) + "\n").encode("utf-8"))
        while True:
            kind, payload = q.get()
            if kind == "close":
                return
            try:
                conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
            except OSError:
                return
