"""http.Client follows redirects itself: headers scoped to an origin
(proxy cookie, proxy Basic auth, the app's Authorization) never reach
another origin; a body is never resent to a redirect target."""
from urllib.parse import quote

import pytest

from conftest import FakeServer
from phosh_toolkit import redirects
from phosh_toolkit.http import NETWORK, Client, HttpError, origin

UA = "Test/1.0"


@pytest.fixture
def other():
    s = FakeServer("server-b").start()
    yield s
    s.stop()


def hop(server, to, status=302):
    return f"{server.url}/redirect?status={status}&to={quote(to, safe='')}"


def test_cross_origin_redirect_drops_origin_scoped_headers(server, other):
    http = Client(UA)
    http.cookies = {origin(server.url): "proxy-session=ok"}
    http.proxy_auth = {origin(server.url): "Basic dTpw"}
    answer = http.request("GET", hop(server, other.url + "/info"),
                          {"Authorization": "MediaBrowser Token=secret",
                           "Accept": "application/json"})
    assert b"server-b" in answer.body
    sent = server.requests[-1][2]
    assert sent["Cookie"] == "proxy-session=ok"
    assert sent["Authorization"] == "MediaBrowser Token=secret"
    received = other.requests[-1][2]
    assert "Cookie" not in received and "Authorization" not in received
    assert received["Accept"] == "application/json"


def test_redirect_back_to_the_origin_gets_its_headers_again(server, other):
    http = Client(UA)
    http.cookies = {origin(server.url): "proxy-session=ok"}
    target = hop(other, server.url + "/info")
    http.request("GET", hop(server, target))
    assert "Cookie" not in other.requests[-1][2]
    assert server.requests[-1][2]["Cookie"] == "proxy-session=ok"


def test_media_stream_follows_redirects_with_scoped_headers(server, other):
    http = Client(UA)
    http.cookies = {origin(server.url): "proxy-session=ok"}
    status, _, stream = http.open("GET", hop(server, other.url + "/media"),
                                  {"Range": "bytes=0-9"})
    assert status == 206
    assert stream.read_bytes(10, None).get_data() == bytes(range(10))
    stream.close(None)
    assert "Cookie" not in other.requests[-1][2]


def test_a_post_body_is_not_resent(server, other):
    http = Client(UA)
    status = http.request("POST", hop(server, other.url + "/info", 307),
                          body=b"p=secret").status
    assert status == 307 and other.requests == []
    http.request("POST", hop(server, other.url + "/info", 302), body=b"p=secret")
    assert other.requests[-1][0] == "GET" and other.bodies == []


def test_endless_redirects_are_an_error(server):
    with pytest.raises(HttpError) as e:
        Client(UA).request("GET", server.url + "/loop")
    assert e.value.kind == NETWORK
    assert len(server.requests) == redirects.MAX_HOPS + 1


def test_a_put_body_reaches_no_redirect_target(server, other):
    http = Client(UA)
    for method in ("PUT", "PATCH", "DELETE"):
        for status in (301, 302, 307, 308):
            answer = http.request(method, hop(server, other.url + "/info", status),
                                  body=b"p=secret")
            assert answer.status == status
    assert other.requests == [] and other.bodies == []


def test_next_hop_rules():
    url = "https://a.example/x"
    y = "https://a.example/y"
    for status in (301, 302, 307, 308):
        for method in ("GET", "HEAD"):
            assert redirects.next_hop(method, url, status, "/y") == (method, y)
        for method in ("PUT", "PATCH", "DELETE", "OPTIONS"):
            assert redirects.next_hop(method, url, status, "/y") is None
    for status in (301, 302):
        assert redirects.next_hop("POST", url, status, "/y") == ("GET", y)
    for status in (307, 308):
        assert redirects.next_hop("POST", url, status, "/y") is None
    assert redirects.next_hop("POST", url, 303, "/y") == ("GET", y)
    assert redirects.next_hop("PUT", url, 303, "/y") == ("GET", y)
    assert redirects.next_hop("HEAD", url, 303, "/y") == ("HEAD", y)
    assert redirects.next_hop("GET", url, 302, "file:///etc/passwd") is None
    assert redirects.next_hop("GET", url, 302, "") is None
    assert redirects.next_hop("GET", url, 200, "/y") is None
