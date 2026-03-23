import json
import unittest

from MCP_Server.connection import AbletonConnection


class FakeSocket(object):
    def __init__(self, responses):
        self.responses = list(responses)
        self.sent = []

    def sendall(self, payload):
        self.sent.append(payload)

    def recv(self, _size):
        if self.responses:
            return self.responses.pop(0)
        return b""

    def settimeout(self, _timeout):
        return None

    def close(self):
        return None


class ConnectionTests(unittest.TestCase):
    def test_receive_message_uses_newline_framing(self):
        connection = AbletonConnection()
        connection.sock = FakeSocket([b'{"ok": true, "state": {"tempo": 120}}\n'])
        response = connection._receive_message()
        self.assertTrue(response["ok"])
        self.assertEqual(response["state"]["tempo"], 120)

    def test_send_message_appends_newline(self):
        fake_socket = FakeSocket([])
        connection = AbletonConnection()
        connection.sock = fake_socket
        connection._send_message({"type": "live_status", "params": {}})
        self.assertEqual(
            fake_socket.sent[0],
            json.dumps({"type": "live_status", "params": {}}).encode("utf-8") + b"\n",
        )


if __name__ == "__main__":
    unittest.main()
