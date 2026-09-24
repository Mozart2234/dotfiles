"""NDJSON client for the herdr Unix domain socket API (v0.9.1).

Verified against herdr v0.9.1 source (src/api/server.rs): a connection reads
exactly one initial request line, then either writes exactly one response
line and closes (`handle_request` branch), or -- for `events.subscribe` --
keeps the connection open and pushes further JSON lines with no `id`
(`stream_subscriptions`, polling every ~100ms; the subscription set itself is
fixed for the connection's lifetime and cannot be extended without
reconnecting). There is no persistent multiplexed request/response session:
each `request()` call opens and closes its own connection.
"""

import json
import os
import socket


DEFAULT_SOCKET_PATH = "~/.config/herdr/herdr.sock"


class HerdrError(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__("{}: {}".format(code, message))


class SubscriptionClosed(Exception):
    """Raised by Subscription.poll() when the server closed the connection."""


def socket_path():
    override = os.environ.get("HERDR_SOCKET_PATH")
    if override:
        return override
    return os.path.expanduser(DEFAULT_SOCKET_PATH)


def _connect(path, timeout):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(path)
    return sock


def _send_line(sock, payload):
    sock.sendall((json.dumps(payload) + "\n").encode("utf-8"))


def _recv_one_line(sock, timeout):
    """Read exactly one newline-terminated line, blocking up to timeout total."""
    sock.settimeout(timeout)
    buf = bytearray()
    while b"\n" not in buf:
        chunk = sock.recv(65536)
        if not chunk:
            return bytes(buf) if buf else None
        buf.extend(chunk)
    line, _, _ = bytes(buf).partition(b"\n")
    return line


class HerdrClient:
    """One request == one connection. See module docstring for why."""

    def __init__(self, path=None, timeout=5.0):
        self.path = path or socket_path()
        self.timeout = timeout
        self._next_id = 0

    def _request_id(self, prefix):
        self._next_id += 1
        return "{}_{}".format(prefix, self._next_id)

    def request(self, method, params=None):
        payload = {
            "id": self._request_id("req"),
            "method": method,
            "params": params or {},
        }
        sock = _connect(self.path, self.timeout)
        try:
            _send_line(sock, payload)
            line = _recv_one_line(sock, self.timeout)
        finally:
            sock.close()

        if line is None:
            raise HerdrError(
                "no_response", "connection closed before a response was received"
            )
        response = json.loads(line.decode("utf-8"))
        if "error" in response:
            error = response["error"]
            raise HerdrError(
                error.get("code", "unknown_error"), error.get("message", "")
            )
        return response.get("result", {})

    def subscribe(self, subscriptions):
        payload = {
            "id": self._request_id("sub"),
            "method": "events.subscribe",
            "params": {"subscriptions": subscriptions},
        }
        sock = _connect(self.path, self.timeout)
        _send_line(sock, payload)
        ack_line = _recv_one_line(sock, self.timeout)
        if ack_line is None:
            sock.close()
            raise HerdrError(
                "no_response", "connection closed before subscription ack"
            )
        ack = json.loads(ack_line.decode("utf-8"))
        if "error" in ack:
            sock.close()
            error = ack["error"]
            raise HerdrError(
                error.get("code", "unknown_error"), error.get("message", "")
            )
        return Subscription(sock)


class Subscription:
    """A live events.subscribe connection.

    Pushed lines are `{"event": ..., "data": ...}` with no `id`. Call
    `poll(timeout)` repeatedly instead of iterating blindly, so a caller can
    interleave this with its own timed work (an animation tick, a periodic
    refresh) instead of blocking forever on the socket.
    """

    def __init__(self, sock):
        self._sock = sock
        self._buf = bytearray()
        self._closed = False

    def poll(self, timeout):
        """Return the next pushed event, or None if none arrived within timeout.

        Raises SubscriptionClosed if the server closed the connection.
        """
        if self._closed:
            raise SubscriptionClosed()

        result = self._read_line(timeout)
        if result is _EOF:
            self.close()
            raise SubscriptionClosed()
        if result is _NO_LINE_YET:
            return None
        return json.loads(result.decode("utf-8"))

    def _line_from_buffer(self):
        idx = self._buf.find(b"\n")
        if idx == -1:
            return None
        line = bytes(self._buf[:idx])
        del self._buf[: idx + 1]
        return line

    def _read_line(self, timeout):
        buffered = self._line_from_buffer()
        if buffered is not None:
            return buffered

        self._sock.settimeout(timeout)
        try:
            chunk = self._sock.recv(65536)
        except socket.timeout:
            return _NO_LINE_YET
        except BlockingIOError:
            # settimeout(0) puts the socket in non-blocking mode, where a
            # would-block recv() raises this instead of socket.timeout.
            return _NO_LINE_YET
        if not chunk:
            return _EOF
        self._buf.extend(chunk)
        buffered = self._line_from_buffer()
        return buffered if buffered is not None else _NO_LINE_YET

    def close(self):
        self._closed = True
        try:
            self._sock.close()
        except OSError:
            pass


_EOF = object()
_NO_LINE_YET = object()
