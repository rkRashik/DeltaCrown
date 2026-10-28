"""Bounded loopback Daphne transport smoke check; synthetic ASGI app, no Django or DB.

Runs on 127.0.0.1:58770 and stops its child in finally. Never pass a production host.
Byte-level normal/pipelining/security cases are also in test_http_transport_security.
"""

import json
import os
import socket
import struct
import subprocess
import sys
import time
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    (root / "Artifacts/security-runtime").mkdir(parents=True, exist_ok=True)
    module = root / "Artifacts/security-runtime/transport_app.py"
    module.write_text(
        "async def application(scope, receive, send):\n    if scope['type']=='http':\n        await send({'type':'http.response.start','status':200,'headers':[]})\n        await send({'type':'http.response.body','body':b'local-qa'})\n    elif scope['type']=='websocket':\n        await receive()\n        await send({'type':'websocket.accept'})\n        while True:\n            event=await receive()\n            if event['type']=='websocket.disconnect': return\n",
        encoding="utf-8",
    )
    env = {
        key: os.environ[key]
        for key in ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "USERPROFILE", "LOCALAPPDATA")
        if key in os.environ
    }
    env["PYTHONPATH"] = str(module.parent)
    log = open(root / "Artifacts/security-runtime/daphne-smoke.log", "w")
    p = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "daphne",
            "-b",
            "127.0.0.1",
            "-p",
            "58770",
            "--websocket-max-message-size",
            "256",
            "--websocket-max-frame-size",
            "256",
            "transport_app:application",
        ],
        env=env,
        stdout=log,
        stderr=log,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def request(payload):
        with socket.create_connection(("127.0.0.1", 58770), timeout=3) as s:
            s.sendall(payload)
            s.settimeout(1)
            out = b""
            try:
                while True:
                    part = s.recv(4096)
                    if not part:
                        break
                    out += part
            except TimeoutError:
                pass
            return out

    try:
        for _ in range(60):
            if p.poll() is not None:
                raise RuntimeError("Daphne failed; inspect log")
            try:
                with socket.create_connection(("127.0.0.1", 58770), timeout=0.2):
                    break
            except OSError:
                time.sleep(0.1)
        result = {
            "python": sys.version,
            "health_status": request(
                b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            )
            .split(b"\r\n")[0]
            .decode(),
        }
        for name, char in [("bare_lf", b"\n"), ("bare_cr", b"\r"), ("vertical_tab", b"\x0b")]:
            response = request(
                b"GET /first HTTP/1.1\r\nHost: localhost\r\nFoo: x"
                + char
                + b"Content-Length: 0\r\n\r\nGET /second HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n"
            )
            result[name] = {
                "responses": response.count(b"HTTP/1.1"),
                "statuses": [
                    line.decode("ascii", "replace")
                    for line in response.split(b"\r\n")
                    if line.startswith(b"HTTP/1.1")
                ],
            }
        with socket.create_connection(("127.0.0.1", 58770), timeout=3) as s:
            s.sendall(
                b"GET /ws HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\nOrigin: http://localhost\r\n\r\n"
            )
            handshake = s.recv(4096)
            result["websocket_upgrade"] = handshake.split(b"\r\n")[0].decode()
            mask = b"abcd"
            payload = b"x" * 512
            frame = (
                b"\x81\xfe"
                + struct.pack("!H", 512)
                + mask
                + bytes(x ^ mask[i % 4] for i, x in enumerate(payload))
            )
            s.sendall(frame)
            s.settimeout(3)
            try:
                close = s.recv(4096)
            except ConnectionResetError:
                close = b""
            result["bounded_frame_rejected"] = not close or close[0] & 15 == 8
            result["close_frame_hex"] = close[:8].hex()
        result["post_frame_health"] = (
            request(b"GET / HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n")
            .split(b"\r\n")[0]
            .decode()
        )
        Path("Artifacts/security-runtime/transport-smoke.json").write_text(
            json.dumps(result, indent=2)
        )
        print(json.dumps(result, indent=2))
        assert (
            result["health_status"] == "HTTP/1.1 200 OK"
            and result["post_frame_health"] == "HTTP/1.1 200 OK"
        )
        for name in ["bare_lf", "bare_cr"]:
            assert result[name]["responses"] == 1 and result[name]["statuses"] == [
                "HTTP/1.1 400 Bad Request"
            ]
        assert (
            result["websocket_upgrade"] == "HTTP/1.1 101 Switching Protocols"
            and result["bounded_frame_rejected"]
        )
    finally:
        p.terminate()
        p.wait(timeout=10)
        log.close()


if __name__ == "__main__":
    main()
