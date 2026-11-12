"""HTTP client, mutual TLS, keyring, certificate file, router and media proxy
against a small test server."""
import json
import os
import urllib.error
import urllib.request

import pytest

from conftest import MEDIA, FakeServer
from phosh_toolkit import router, tls
from phosh_toolkit.certificate import CertificateFile
from phosh_toolkit.http import (AUTH, CERTIFICATE_REQUIRED, NETWORK, Client,
                                HttpError, is_certificate_page)
from phosh_toolkit.keyring import CERTIFICATE_PASSWORD, Keyring
from phosh_toolkit.proxy import MediaProxy
from phosh_toolkit.route import LOCAL, REMOTE
from phosh_toolkit.testing import P12_PASSWORD, run_until

UA = "Test/1.0 (+https://example.org)"


def client(trust=None, certificate=None):
    http = Client(UA)
    http.tls_database = trust
    http.certificate = certificate
    return http


def p12(pki):
    return tls.load((pki / "client.p12").read_bytes(), P12_PASSWORD)


def info(http):
    def probe(url, timeout):
        answer = json.loads(http.request("GET", url + "/info", timeout=timeout).body)
        return answer["id"], answer
    return probe


@pytest.fixture
def keyring():
    k = Keyring("de.nexumia.Test", {CERTIFICATE_PASSWORD: "Test password"},
                memory_env="PHOSH_TOOLKIT_TEST_KEYRING")
    yield k
    k.forget_memory()


def test_user_agent_and_errors(server):
    http = client()
    http.request("GET", server.url + "/info")
    assert server.requests[-1][2]["User-Agent"] == UA
    with pytest.raises(HttpError) as e:
        http.request("GET", server.url + "/private")
    assert e.value.kind == AUTH
    with pytest.raises(HttpError) as e:
        http.request("GET", server.url + "/nginx")
    assert e.value.kind == CERTIFICATE_REQUIRED
    with pytest.raises(HttpError) as e:
        http.request("GET", "http://127.0.0.1:9/info", timeout=3)
    assert e.value.kind == NETWORK


def test_certificate_formats(pki):
    assert tls.describe(p12(pki))[0] == "Robin's phone"
    tls.load((pki / "client-combined.pem").read_bytes())
    with pytest.raises(tls.PasswordNeeded):
        tls.load((pki / "client.p12").read_bytes(), "wrong")
    with pytest.raises(tls.CertificateError):
        tls.load((pki / "client.pem").read_bytes())   # no key
    with pytest.raises(tls.CertificateError):
        tls.load(b"\x00garbage")


def test_mtls_requires_the_client_certificate(mtls_server, pki, trust):
    with pytest.raises(HttpError) as e:
        client(trust).request("GET", mtls_server.url + "/info")
    assert e.value.kind == CERTIFICATE_REQUIRED
    answer = client(trust, p12(pki)).request("GET", mtls_server.url + "/info")
    assert json.loads(answer.body) == {"id": "server-a"}


def test_nginx_certificate_page():
    assert is_certificate_page(b"<html><head><title>400 No required SSL "
                               b"certificate was sent</title></head>")
    assert not is_certificate_page(b'{"Id": "abc"}')


def test_keyring_in_memory(keyring):
    assert keyring.lookup("token") is None
    keyring.store("token", "t")
    assert keyring.lookup("token") == "t"
    keyring.clear("token")
    assert keyring.lookup("token") is None


def test_certificate_file(tmp_path, pki, keyring):
    file = CertificateFile(tmp_path / "app" / "client-certificate", keyring)
    file.save((pki / "client.p12").read_bytes(), P12_PASSWORD)
    assert os.stat(file.path).st_mode & 0o777 == 0o600
    assert keyring.lookup(CERTIFICATE_PASSWORD) == P12_PASSWORD
    assert file.load().props.private_key
    assert file.describe().startswith("Robin's phone, valid until ")
    file.delete()
    assert not file.path.exists()
    assert keyring.lookup(CERTIFICATE_PASSWORD) is None
    assert file.describe().startswith("Can't be used: ")


class Route(router.Router):
    def __init__(self, http, remote, local, home=(), expected=""):
        super().__init__(watch=False)
        self.http = http
        self._addresses = (remote, local, list(home))
        self.expected = expected
        self.found = None
        self.signed_out = False

    def probe(self, url, timeout):
        return info(self.http)(url, timeout)

    def addresses(self):
        return self._addresses

    def server_id(self):
        return self.expected

    def resolved(self, kind, url, answer):
        self.found = (kind, url, answer)

    def unauthorized(self):
        self.signed_out = True


def resolve(conn):
    done = []
    conn.resolve(lambda e: done.append(e))
    run_until(lambda: done)
    return done[0]


@pytest.fixture
def ssids(monkeypatch):
    current = {"value": None}
    monkeypatch.setattr(router.network, "current_ssids", lambda: current["value"])
    return current


def test_home_network_uses_local(server, ssids):
    ssids["value"] = {"Home"}
    conn = Route(client(), "https://unreachable.invalid", server.url, ["Home"])
    assert resolve(conn) is None
    assert conn.state == LOCAL and conn.base_url == server.url
    assert conn.found == (LOCAL, server.url, {"id": "server-a"})


def test_away_uses_remote(server, ssids):
    ssids["value"] = {"Café"}
    conn = Route(client(), server.url, "http://127.0.0.1:9", ["Home"])
    assert resolve(conn) is None
    assert conn.state == REMOTE


def test_local_down_falls_back_to_remote(server, ssids):
    # Port 9 (discard) is closed: the local probe fails fast.
    ssids["value"] = {"Home"}
    conn = Route(client(), server.url, "http://127.0.0.1:9", ["Home"])
    assert resolve(conn) is None
    assert conn.state == REMOTE


def test_other_server_is_skipped(server, ssids):
    conn = Route(client(), "", server.url, expected="server-b")
    assert isinstance(resolve(conn), HttpError)
    assert conn.state == router.OFFLINE and conn.base_url == ""


def test_remote_certificate_error_wins(mtls_server, trust, ssids):
    conn = Route(client(trust), mtls_server.url, "http://127.0.0.1:9")
    error = resolve(conn)
    assert error.kind == CERTIFICATE_REQUIRED and conn.error is error


def test_call_reports_401_and_retries_after_network_error(server, ssids):
    conn = Route(client(), server.url, "")
    done = []
    conn.call(lambda: conn.http.request("GET", conn.base_url + "/private"),
              lambda r, e: done.append(e))
    run_until(lambda: done)
    assert done[0].kind == AUTH and conn.signed_out
    # A stale address: the call resolves again and succeeds.
    conn.base_url = "http://127.0.0.1:9"
    done.clear()
    conn.call(lambda: conn.http.request("GET", conn.base_url + "/info"),
              lambda r, e: done.append((r, e)))
    run_until(lambda: done)
    assert done[0][1] is None and conn.base_url == server.url


def test_probe_addresses(server, ssids):
    done = []
    router.probe_addresses(info(client()), server.url, "http://127.0.0.1:9",
                           lambda r, e: done.append((r, e)))
    run_until(lambda: done)
    answers, error = done[0]
    assert error is None
    assert answers[REMOTE] == {"id": "server-a"}
    assert isinstance(answers[LOCAL], HttpError)


def test_probe_addresses_rejects_two_servers(server):
    other = FakeServer("server-b").start()
    try:
        done = []
        router.probe_addresses(info(client()), server.url, other.url,
                               lambda r, e: done.append(e))
        run_until(lambda: done)
        assert "different servers" in str(done[0])
    finally:
        other.stop()


def test_proxy_forwards_ranges_through_mtls(mtls_server, pki, trust):
    http = client(trust, p12(pki))
    proxy = MediaProxy(lambda path: (http, mtls_server.url + path + "&t=secret",
                                     {"Authorization": "Bearer good"}))
    try:
        url = proxy.url("/media?id=1")
        assert "secret" not in url.split(proxy.secret)[1]
        request = urllib.request.Request(url, headers={"Range": "bytes=256-511"})
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 206
            assert response.headers["Content-Range"] == f"bytes 256-511/{len(MEDIA)}"
            assert response.read() == MEDIA[256:512]
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url.replace(proxy.secret, "guess"), timeout=10)
    finally:
        proxy.stop()
    method, path, headers = mtls_server.requests[-1]
    assert path == "/media?id=1&t=secret"
    assert headers["Authorization"] == "Bearer good"


def test_proxy_posts_a_form_body(server):
    http = client()
    proxy = MediaProxy(lambda path: (http, server.url + path, {},
                                     b"u=robin&t=secret"))
    try:
        url = proxy.url("/media?id=1")
        request = urllib.request.Request(url, headers={"Range": "bytes=0-9"})
        with urllib.request.urlopen(request, timeout=10) as response:
            assert response.status == 206 and response.read() == MEDIA[:10]
    finally:
        proxy.stop()
    method, path, headers = server.requests[-1]
    assert (method, path) == ("POST", "/media?id=1")
    assert server.bodies == [b"u=robin&t=secret"]
    assert headers["Content-Type"] == "application/x-www-form-urlencoded"


def test_strict_router_skips_local_without_networkmanager(server, ssids):
    conn = Route(client(), "", server.url, ["Home"])
    conn.strict_local = True
    assert isinstance(resolve(conn), HttpError)
    ssids["value"] = {"Home"}
    assert resolve(conn) is None and conn.state == LOCAL


def test_proxy_answers_502_when_forward_fails():
    def forward(path):
        raise RuntimeError("not signed in")
    proxy = MediaProxy(forward)
    try:
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(proxy.url("/media"), timeout=10)
        assert e.value.code == 502
    finally:
        proxy.stop()


def test_network_change_during_a_search_searches_again(server, ssids):
    """Wi-Fi drops while a search still sees it: the change that comes in
    meanwhile is not lost, and the remote address wins."""
    import threading
    local = FakeServer("server-a").start()
    try:
        gate = threading.Event()
        conn = Route(client(), server.url, local.url, ["Home"])
        conn.strict_local = True
        plain_probe = conn.probe

        def slow_probe(url, timeout):
            gate.wait(5)           # the network changes during this probe
            return plain_probe(url, timeout)
        conn.probe = slow_probe
        ssids["value"] = {"Home"}
        done = []
        conn.resolve(lambda e: done.append(e))
        # Wi-Fi gone, the watcher asks again while the first search runs.
        ssids["value"] = set()
        conn.resolve()
        gate.set()
        run_until(lambda: done)
        assert done[0] is None
        assert conn.state == REMOTE and conn.base_url == server.url
    finally:
        local.stop()


def test_watcher_listens_to_networkmanager():
    from gi.repository import GLib

    from phosh_toolkit import network

    class Bus:
        def signal_subscribe(self, *args):
            self.args = args
            return 7

        def signal_unsubscribe(self, sid):
            self.unsubscribed = sid
    bus = Bus()
    watcher = network.Watcher(bus=bus)
    assert bus.args[:4] == (network.NM, network.PROPS, "PropertiesChanged",
                            network.NM_PATH)
    changes = []
    watcher.connect("changed", lambda w: changes.append(1))
    # A property that doesn't touch the route: nothing.
    watcher._on_nm(bus, network.NM, network.NM_PATH, network.PROPS,
                   "PropertiesChanged", GLib.Variant("(sa{sv}as)", (
                       network.NM, {"WirelessEnabled": GLib.Variant("b", True)}, [])))
    watcher._on_nm(bus, network.NM, network.NM_PATH, network.PROPS,
                   "PropertiesChanged", GLib.Variant("(sa{sv}as)", (
                       network.NM, {"PrimaryConnection": GLib.Variant("o", "/x")}, [])))
    run_until(lambda: changes, 5)
    assert changes == [1]
    watcher.close()
    assert bus.unsubscribed == 7


def test_proxy_follows_the_route(server):
    """A changed route cuts the running upstream read, so the player
    reconnects through the new address."""
    import http.client
    import time
    from urllib.parse import urlsplit
    other = FakeServer("server-b").start()
    try:
        current = {"url": server.url}
        proxy = MediaProxy(lambda path: (client(), current["url"] + path, {}))
        conn = Route(client(), server.url, "")
        conn.base_url = server.url
        proxy.follow(conn)
        parts = urlsplit(proxy.url("/media"))
        c = http.client.HTTPConnection(parts.hostname, parts.port, timeout=10)
        c.request("GET", parts.path)
        response = c.getresponse()
        response.read(1000)
        deadline = time.time() + 5
        while not proxy._active and time.time() < deadline:
            time.sleep(0.05)
        assert proxy._active
        # The route moves to the other server.
        current["url"] = conn.base_url = other.url
        conn.emit("state-changed")
        rest = b""
        try:
            while True:
                chunk = response.read(65536)
                if not chunk:
                    break
                rest += chunk
        except http.client.IncompleteRead as e:
            rest += e.partial
        assert len(rest) + 1000 < int(response.getheader("Content-Length"))
        c.close()
        proxy.stop()
    finally:
        other.stop()


def test_proxy_follows_its_router_by_itself(server):
    """MediaProxy(connection.forward) needs no follow() call."""
    class Conn(Route):
        def forward(self, path):
            return client(), self.base_url + path, {}
    conn = Conn(client(), server.url, "")
    proxy = MediaProxy(conn.forward)
    assert proxy._following is conn
    calls = []
    proxy.reroute = lambda: calls.append(1)
    conn.base_url = server.url
    conn.emit("state-changed")
    proxy.follow(conn)          # again: no second handler
    conn.base_url = "http://127.0.0.1:9"
    conn.emit("state-changed")
    assert calls == [1]
    # A plain function has no router to follow.
    assert MediaProxy(lambda path: None)._following is None


def test_proxy_log_has_no_secret_and_no_query(server, caplog):
    http = client()
    proxy = MediaProxy(lambda path: (http, server.url + path, {}, None))
    caplog.set_level("DEBUG", logger="phosh_toolkit.proxy")
    try:
        url = proxy.url("/media?api_key=token")
        request = urllib.request.Request(url, headers={"Range": "bytes=0-9"})
        with urllib.request.urlopen(request, timeout=10) as response:
            response.read()
        secret = proxy.secret
    finally:
        proxy.stop()
    logged = caplog.text
    assert "/media" in logged
    assert secret not in logged and "api_key" not in logged
