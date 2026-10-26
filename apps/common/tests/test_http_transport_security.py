"""Bounded upstream HTTP parser/backport regression tests; no sockets or DB."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import unittest

from twisted.internet.testing import StringTransport
from twisted.web import http


class RecordingRequest(http.Request):
    def process(self):
        self.channel.seen.append(self.uri)
        self.setHeader(b"content-length", b"2")
        self.write(b"ok")
        self.finish()


class HTTPHeaderSecurityTests(unittest.TestCase):
    def channel(self):
        channel = http.HTTPChannel()
        channel.factory = http.HTTPFactory()
        channel.requestFactory = RecordingRequest
        channel.seen = []
        transport = StringTransport()
        channel.makeConnection(transport)
        self.addCleanup(channel.connectionLost, None)
        return channel, transport

    def test_upstream_invalid_header_values_disconnect_without_dispatch(self):
        # Exact bounded cases in upstream 1616f702, plus pre-existing NUL rejection.
        for value in [
            b"a\nContent-Length: 5",
            b"a\rContent-Length: 5",
            b"a\nb",
            b"a\rb",
            b"a\x00b",
        ]:
            with self.subTest(value=value):
                channel, transport = self.channel()
                channel.dataReceived(
                    b"GET / HTTP/1.1\r\nHost: localhost\r\nX-QA: " + value + b"\r\n\r\n"
                )
                self.assertTrue(transport.disconnecting)
                self.assertEqual(transport.value(), b"HTTP/1.1 400 Bad Request\r\n\r\n")
                self.assertEqual(channel.seen, [])

    def test_valid_headers_and_pipelining_remain_supported(self):
        channel, transport = self.channel()
        channel.dataReceived(
            b"GET /first HTTP/1.1\r\nHost: localhost\r\nX-QA: valid\tvalue\r\n\r\n"
            b"GET /second HTTP/1.1\r\nHost: localhost\r\n\r\n"
        )
        self.assertEqual(channel.seen, [b"/first", b"/second"])
        self.assertEqual(transport.value().count(b"HTTP/1.1 200 OK"), 2)
        self.assertFalse(transport.disconnecting)

    def test_malformed_pipelining_never_dispatches_either_request(self):
        for value in [b"a\nContent-Length: 0", b"a\rContent-Length: 0"]:
            channel, transport = self.channel()
            channel.dataReceived(
                b"GET /first HTTP/1.1\r\nHost: localhost\r\nX-QA: " + value + b"\r\n\r\n"
                b"GET /second HTTP/1.1\r\nHost: localhost\r\n\r\n"
            )
            self.assertEqual(channel.seen, [])
            self.assertTrue(transport.disconnecting)
            self.assertEqual(transport.value().count(b"HTTP/1.1"), 1)

    def test_split_header_value_is_rejected_after_network_chunk_boundary(self):
        channel, transport = self.channel()
        channel.dataReceived(b"GET / HTTP/1.1\r\nHost: localhost\r\nX-QA: a")
        self.assertEqual(transport.value(), b"")
        channel.dataReceived(b"\nContent-Length: 0\r\n\r\n")
        self.assertTrue(transport.disconnecting)
        self.assertEqual(channel.seen, [])

    def test_installed_parser_matches_reviewed_backport(self):
        root = Path(__file__).resolve().parents[3]
        provenance = json.loads((root / "vendor/twisted/provenance.json").read_text())
        self.assertEqual(version("Twisted"), provenance["version"])
        self.assertEqual(
            hashlib.sha256(Path(http.__file__).read_bytes()).hexdigest(),
            provenance["patched_http_sha256"],
        )
