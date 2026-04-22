"""
Force an immediate page reload on the running Chromium kiosk by sending
Page.reload via the Chrome DevTools Protocol websocket.

Called from scripts/refresh.sh --hard. Uses only the Python stdlib so it
works with or without the project's venv.

The kiosk is launched with --remote-debugging-port=9222 (see the labwc
autostart), which exposes:
  - HTTP:  GET /json      -> list of tabs, each with a webSocketDebuggerUrl
  - WS:    that URL       -> full CDP over websocket
The HTTP endpoints alone can't trigger a reload; we have to speak WS.
"""

from __future__ import annotations

import base64
import json
import os
import socket
import struct
import sys
import urllib.parse
import urllib.request

DEBUG_PORT = 9222
TARGET_URL_FRAGMENT = "localhost:5000"


def find_target_ws_url() -> str:
    """Return the webSocketDebuggerUrl for the piCalendar tab."""
    with urllib.request.urlopen(
        f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=3
    ) as resp:
        tabs = json.load(resp)

    pages = [t for t in tabs if t.get("type") == "page"]
    if not pages:
        raise RuntimeError("no page-type targets found on port 9222")

    for t in pages:
        if TARGET_URL_FRAGMENT in t.get("url", ""):
            return t["webSocketDebuggerUrl"]

    # Fall back to the first page target if nothing matches exactly.
    return pages[0]["webSocketDebuggerUrl"]


def _ws_handshake(sock: socket.socket, host: str, port: int, path: str) -> None:
    key = base64.b64encode(os.urandom(16)).decode()
    req = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        f"Upgrade: websocket\r\n"
        f"Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        f"Sec-WebSocket-Version: 13\r\n\r\n"
    )
    sock.sendall(req.encode())

    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("websocket handshake: empty response")
        buf += chunk

    status_line = buf.split(b"\r\n", 1)[0]
    if b" 101 " not in status_line:
        raise RuntimeError(f"websocket handshake failed: {status_line!r}")


def _ws_send_text(sock: socket.socket, payload: bytes) -> None:
    """Send a single masked text frame (client -> server must mask)."""
    mask = os.urandom(4)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    header = bytes([0x81])  # FIN + text opcode
    length = len(payload)
    if length < 126:
        header += bytes([0x80 | length])
    elif length < 65536:
        header += bytes([0x80 | 126]) + struct.pack(">H", length)
    else:
        header += bytes([0x80 | 127]) + struct.pack(">Q", length)
    sock.sendall(header + mask + masked)


def reload_tab(ws_url: str) -> None:
    url = urllib.parse.urlparse(ws_url)
    host = url.hostname or "127.0.0.1"
    port = url.port or DEBUG_PORT
    path = url.path or "/"

    sock = socket.create_connection((host, port), timeout=5)
    try:
        _ws_handshake(sock, host, port, path)
        msg = json.dumps(
            {"id": 1, "method": "Page.reload", "params": {"ignoreCache": True}}
        ).encode()
        _ws_send_text(sock, msg)
        # Give Chromium a moment to ack before we tear down the connection,
        # otherwise it sometimes drops the command.
        try:
            sock.settimeout(1.0)
            sock.recv(4096)
        except socket.timeout:
            pass
    finally:
        sock.close()


def main() -> int:
    try:
        ws_url = find_target_ws_url()
    except Exception as e:
        print(f"cdp_reload: couldn't find target tab: {e}", file=sys.stderr)
        return 1
    try:
        reload_tab(ws_url)
    except Exception as e:
        print(f"cdp_reload: reload failed: {e}", file=sys.stderr)
        return 1
    print("    reload sent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
