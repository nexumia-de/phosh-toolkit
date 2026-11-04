"""Fixtures for the shared package: a small HTTP(S) server that answers
like an app's server, optionally behind mutual TLS."""
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
os.environ["PHOSH_TOOLKIT_TEST_KEYRING"] = "memory"

from gi.repository import Gio  # noqa: E402

from phosh_toolkit import testing  # noqa: E402

MEDIA = bytes(range(256)) * 4096   # 1 MiB for range tests


class FakeServer:
    """GET /info answers {"id": server_id}; /media serves MEDIA with
    ranges; /private needs "Authorization: Bearer good" (else 401); /nginx
    answers like nginx without a client certificate."""

    def __init__(self, server_id="server-a", context=None):
        self.server_id = server_id
        self.requests = []
        owner = self

        class Handler(_Handler):
            server_owner = owner

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.httpd.daemon_threads = True
        self.scheme = "http"
        if context is not None:
            self.httpd.socket = context.wrap_socket(self.httpd.socket,
                                                    server_side=True)
            self.scheme = "https"

    @property
    def url(self):
        host, port = self.httpd.server_address
        return f"{self.scheme}://{host}:{port}"

    def start(self):
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self.httpd.shutdown()
        self.httpd.server_close()


class _Handler(BaseHTTPRequestHandler):
    server_owner = None
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):
        pass

    def _send(self, status, body, content_type="application/json", extra=()):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra:
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        owner = self.server_owner
        owner.requests.append((self.command, self.path, dict(self.headers)))
        path = self.path.split("?")[0]
        if path == "/info":
            self._send(200, json.dumps({"id": owner.server_id}).encode())
        elif path == "/private":
            ok = self.headers.get("Authorization") == "Bearer good"
            self._send(200 if ok else 401, b"{}")
        elif path == "/nginx":
            self._send(400, b"<html><head><title>400 No required SSL "
                       b"certificate was sent</title></head></html>",
                       "text/html")
        elif path == "/media":
            start, end = 0, len(MEDIA) - 1
            status, extra = 200, [("Accept-Ranges", "bytes")]
            spec = self.headers.get("Range")
            if spec and spec.startswith("bytes="):
                first, _, last = spec[6:].partition("-")
                start = int(first)
                end = int(last) if last else end
                status = 206
                extra.append(("Content-Range", f"bytes {start}-{end}/{len(MEDIA)}"))
            self._send(status, MEDIA[start:end + 1], "audio/flac", extra)
        else:
            self._send(404, b"{}")


@pytest.fixture
def server():
    s = FakeServer().start()
    yield s
    s.stop()


@pytest.fixture(scope="session")
def pki(tmp_path_factory):
    return testing.make_pki(tmp_path_factory.mktemp("pki"))


@pytest.fixture
def mtls_server(pki):
    s = FakeServer(context=testing.server_context(pki)).start()
    yield s
    s.stop()


@pytest.fixture
def trust(pki):
    return Gio.TlsFileDatabase.new(str(pki / "ca.pem"))
