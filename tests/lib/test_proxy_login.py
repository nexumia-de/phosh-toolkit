"""A reverse proxy with its own login in front of the server: detected,
signed in through the web view (also with mutual TLS), cookies kept and
sent, an expired proxy session not mistaken for a rejected server login."""
import json
import os
import urllib.request

import pytest
from gi.repository import Gio

from conftest import FakeServer
from phosh_toolkit import proxy_login, route, router, testing, tls
from phosh_toolkit.http import AUTH, PROXY_LOGIN, Client, HttpError, origin
from phosh_toolkit.keyring import Keyring
from phosh_toolkit.proxy import MediaProxy
from phosh_toolkit.testing import P12_PASSWORD, run_until

UA = "Test/1.0"
COOKIE = "proxy-session=ok"


def info(http, url, timeout=10):
    answer = json.loads(http.request("GET", url + "/info", {"Accept": "application/json"},
                                     timeout=timeout).body)
    return answer["id"], answer


@pytest.fixture
def proxied():
    s = FakeServer()
    s.login = True
    s.start()
    yield s
    s.stop()


@pytest.fixture
def keyring():
    k = Keyring("de.nexumia.Test", {}, memory_env="PHOSH_TOOLKIT_TEST_KEYRING")
    yield k
    k.forget_memory()


def test_web_page_instead_of_json_is_a_proxy_login(server):
    with pytest.raises(HttpError) as e:
        Client(UA).request("GET", server.url + "/page", {"Accept": "application/json"})
    assert e.value.kind == PROXY_LOGIN and e.value.url == server.url + "/page"
    # Without asking for JSON a page is just a page.
    assert Client(UA).request("GET", server.url + "/page").status == 200


def test_cookies_go_only_to_their_origin(proxied, server):
    http = Client(UA)
    http.cookies = {origin(proxied.url): COOKIE}
    assert info(http, proxied.url)[0] == "server-a"
    info(http, server.url)
    assert "Cookie" not in server.requests[-1][2]
    assert origin("https://Example.org/x") == "https://example.org:443"
    assert origin("http://10.0.0.2:8096") == "http://10.0.0.2:8096"


def test_cookie_jar(keyring):
    jar = proxy_login.CookieJar(keyring)
    assert jar.load() == {}
    jar.save({"https://a:443": COOKIE})
    assert jar.load() == {"https://a:443": COOKIE}
    jar.save({})
    assert keyring.lookup(proxy_login.COOKIES) is None


class Route(router.Router):
    def __init__(self, http, url):
        super().__init__(watch=False)
        self.http, self.url = http, url
        self.logins, self.signed_out = [], False
        self.connect("proxy-login", lambda r, url: self.logins.append(url))

    def probe(self, url, timeout):
        return info(self.http, url, timeout)

    def addresses(self):
        return self.url, "", []

    def unauthorized(self):
        self.signed_out = True


def resolve(conn):
    done = []
    conn.resolve(lambda e: done.append(e))
    run_until(lambda: done)
    return done[0]


@pytest.fixture
def no_wifi(monkeypatch):
    monkeypatch.setattr(router.network, "current_ssids", lambda: None)


def test_router_reports_the_proxy_login(proxied, no_wifi):
    conn = Route(Client(UA), proxied.url)
    error = resolve(conn)
    assert error.kind == PROXY_LOGIN and conn.state == router.OFFLINE
    assert conn.logins == [proxied.url]
    conn.http.cookies = {origin(proxied.url): COOKIE}
    assert resolve(conn) is None and conn.state == route.REMOTE


def test_expired_proxy_session_is_not_a_server_sign_out(proxied, no_wifi):
    http = Client(UA)
    http.cookies = {origin(proxied.url): COOKIE}
    conn = Route(http, proxied.url)
    assert resolve(conn) is None
    http.cookies = {}       # the proxy's session ran out
    done = []
    conn.call(lambda: http.request("GET", conn.base_url + "/private"),
              lambda r, e: done.append(e))
    run_until(lambda: done)
    assert done[0].kind == PROXY_LOGIN and not conn.signed_out
    assert conn.logins == [proxied.url]
    # With the proxy session the server's own 401 still signs out.
    http.cookies = {origin(proxied.url): COOKIE}
    done.clear()
    conn.call(lambda: http.request("GET", conn.base_url + "/private"),
              lambda r, e: done.append(e))
    run_until(lambda: done)
    assert done[0].kind == AUTH and conn.signed_out


def test_media_proxy_sends_the_proxy_cookie(proxied):
    http = Client(UA)
    http.cookies = {origin(proxied.url): COOKIE}
    proxy = MediaProxy(lambda path: (http, proxied.url + path, {}))
    try:
        with urllib.request.urlopen(proxy.url("/media"), timeout=10) as response:
            assert response.status == 200
    finally:
        proxy.stop()
    assert COOKIE in proxied.requests[-1][2]["Cookie"]


# --- the login window (WebKitGTK 6, needs a display) ------------------------

needs_webkit = pytest.mark.skipif(
    not proxy_login.available()
    or not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    or not testing.webkit_sandbox_works(),
    reason="needs WebKitGTK 6, a display and a working bubblewrap sandbox")


@pytest.fixture
def mtls_proxied(pki):
    s = FakeServer(context=testing.server_context(pki))
    s.login = True
    s.start()
    yield s
    s.stop()


@needs_webkit
def test_login_page_signs_in_through_mutual_tls(mtls_proxied, pki, trust):
    import gi
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    Adw.init()
    http = Client(UA)
    http.tls_database = trust
    http.certificate = tls.load((pki / "client.p12").read_bytes(), P12_PASSWORD)
    server_cert = Gio.TlsCertificate.new_from_file(str(pki / "server.pem"))
    got = []
    page = proxy_login.make_page(
        mtls_proxied.url, mtls_proxied.url, http, info, got.append,
        trusted=[(server_cert, "127.0.0.1")])
    nav = Adw.NavigationView()
    nav.push(page)
    run_until(lambda: got, 30)
    assert got == [COOKIE]
    # The web view went through the redirect, the login form and back.
    paths = [p for _, p, _ in mtls_proxied.requests]
    assert "/auth/login" in paths and paths.count("/info") >= 2
    assert http.cookies == {}       # the app's client is left alone


# --- HTTP Basic auth at the proxy (Pangolin's header authentication) ---


@pytest.fixture
def basic():
    s = FakeServer()
    s.basic = "phone:s3cret"
    s.start()
    yield s
    s.stop()


def test_basic_challenge_is_a_basic_proxy_login(basic, no_wifi):
    conn = Route(Client(UA), basic.url)
    error = resolve(conn)
    assert error.kind == PROXY_LOGIN and error.wants_basic
    assert conn.proxy_error is error and conn.logins == [basic.url]
    # No web page for it: the app points to its form instead.
    shown = []
    assert proxy_login.sign_in(None, conn, conn.http, None, None,
                               on_basic=lambda: shown.append(1)) is None
    assert shown == [1]


def test_basic_credentials_go_only_to_their_origin(basic, server, no_wifi, keyring):
    creds = proxy_login.ProxyCredentials(keyring)
    assert creds.get(basic.url) == ("", "")
    creds.set(basic.url + "/some/path", "phone", "s3cret")
    assert creds.get(basic.url) == ("phone", "s3cret")
    http = Client(UA)
    http.proxy_auth = creds.headers()
    conn = Route(http, basic.url)
    assert resolve(conn) is None
    assert basic.requests[-1][2]["Authorization"].startswith("Basic ")
    info(http, server.url)
    assert "Authorization" not in server.requests[-1][2]
    creds.set(basic.url, "", "")
    assert creds.load() == {} and keyring.lookup(proxy_login.CREDENTIALS) is None


def test_app_authorization_header_wins(basic):
    http = Client(UA)
    http.proxy_auth = {origin(basic.url): "Basic xyz"}
    with pytest.raises(HttpError) as e:
        http.request("GET", basic.url + "/private", {"Authorization": "Bearer good"})
    # The proxy got the app's header, not the Basic one, and refused.
    assert e.value.kind == AUTH and e.value.wants_basic
    assert basic.requests[-1][2]["Authorization"] == "Bearer good"


def test_wrong_basic_credentials_are_not_a_server_sign_out(basic, no_wifi):
    http = Client(UA)
    http.proxy_auth = {origin(basic.url): proxy_login.basic_auth("phone", "s3cret")}
    conn = Route(http, basic.url)
    assert resolve(conn) is None
    http.proxy_auth = {origin(basic.url): proxy_login.basic_auth("phone", "old")}
    done = []
    conn.call(lambda: http.request("GET", conn.base_url + "/info"),
              lambda r, e: done.append(e))
    run_until(lambda: done)
    assert done[0].kind == PROXY_LOGIN and done[0].wants_basic
    assert not conn.signed_out


def test_media_proxy_sends_basic_auth(basic):
    http = Client(UA)
    http.proxy_auth = {origin(basic.url): proxy_login.basic_auth("phone", "s3cret")}
    proxy = MediaProxy(lambda path: (http, basic.url + path, {}))
    try:
        with urllib.request.urlopen(proxy.url("/media"), timeout=10) as response:
            assert response.status == 200
    finally:
        proxy.stop()
