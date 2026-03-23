from __future__ import annotations

import json
import logging
import socket
import threading
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger("AbletonMCPServer")


@dataclass
class AbletonConnection:
    host: str = "127.0.0.1"
    port: int = 9877
    timeout_seconds: float = 15.0
    sock: socket.socket | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _recv_buffer: str = field(default="", init=False, repr=False)

    def connect(self) -> None:
        if self.sock is not None:
            return

        sock = socket.create_connection((self.host, self.port), timeout=self.timeout_seconds)
        sock.settimeout(self.timeout_seconds)
        self.sock = sock
        self._recv_buffer = ""
        logger.info("Connected to Ableton bridge at %s:%s", self.host, self.port)

    def disconnect(self) -> None:
        if self.sock is None:
            return

        try:
            self.sock.close()
        except OSError:
            logger.debug("Ignoring socket close error", exc_info=True)
        finally:
            self.sock = None
            self._recv_buffer = ""

    def send_command(self, command_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = {"type": command_type, "params": params or {}}
        last_error: Exception | None = None

        with self._lock:
            for _attempt in range(2):
                try:
                    self.connect()
                    self._send_message(payload)
                    return self._receive_message()
                except (OSError, socket.timeout, json.JSONDecodeError) as exc:
                    last_error = exc
                    self.disconnect()

        raise ConnectionError(
            "Could not communicate with Ableton. Make sure the Remote Script is loaded."
        ) from last_error

    def _send_message(self, payload: dict[str, Any]) -> None:
        if self.sock is None:
            raise ConnectionError("Socket is not connected")

        message = json.dumps(payload).encode("utf-8") + b"\n"
        self.sock.sendall(message)

    def _receive_message(self) -> dict[str, Any]:
        if self.sock is None:
            raise ConnectionError("Socket is not connected")

        while "\n" not in self._recv_buffer:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("Ableton bridge closed the connection")
            self._recv_buffer += chunk.decode("utf-8")

        raw_message, self._recv_buffer = self._recv_buffer.split("\n", 1)
        if not raw_message.strip():
            raise json.JSONDecodeError("Received empty response", raw_message, 0)

        return json.loads(raw_message)


_ableton_connection: AbletonConnection | None = None


def get_ableton_connection() -> AbletonConnection:
    global _ableton_connection

    if _ableton_connection is None:
        _ableton_connection = AbletonConnection()

    return _ableton_connection
