"""HTTP with libsoup 3 from worker threads, with an optional client
certificate. Every thread gets its own SoupSession, so connections are
reused within a thread and no session is shared between threads.
No GTK."""
import base64
import threading
from urllib.parse import urlsplit

import gi

gi.require_version("Soup", "3.0")
from gi.repository import Gio, GLib, Soup  # noqa: E402

from phosh_toolkit import redirects  # noqa: E402
# origin() is part of this module's interface.
from phosh_toolkit.redirects import origin  # noqa: E402,F401

NETWORK = "network"          # no route, DNS, refused, timeout
TLS = "tls"                  # handshake failed, untrusted server
CERTIFICATE_REQUIRED = "certificate-required"
AUTH = "auth"                # 401
SERVER = "server"            # other HTTP errors
# A reverse proxy in front of the server wants its own login (SSO);
# HttpError.url is the address to open in the login window.
PROXY_LOGIN = "proxy-login"


class HttpError(Exception):
    """`challenge` is the WWW-Authenticate header of a 401, e.g.
    'Basic realm="pangolin"': a proxy that wants HTTP Basic auth."""

    def __init__(self, kind, message, status=0, url="", challenge=""):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.url = url
        self.challenge = challenge

    @property
    def wants_basic(self):
        return self.challenge.lower().startswith("basic")


def page_url(url):
    """`url` without user info, query and fragment: what may be shown or
    opened in a login window. A query can carry credentials or tokens,
    and the proxy passes the address on to its identity provider."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:
        host = f"[{host}]"
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}{parts.path}"


def _shown(url):
    """page_url(url) for messages and log lines, also for an address
    urlsplit rejects."""
    try:
        return page_url(url)
    except ValueError:
        return url.split("?")[0].split("#")[0].rpartition("@")[2]


def proxy_login(url, challenge=""):
    url = page_url(url)
    if challenge.lower().startswith("basic"):
        return HttpError(PROXY_LOGIN, "The proxy in front of the server asks "
                         "for its user name and password", url=url,
                         challenge=challenge)
    return HttpError(PROXY_LOGIN, "The proxy in front of the server asks for "
                     "its own login", url=url, challenge=challenge)


def basic_auth(user, password):
    """The Authorization header value of HTTP Basic auth."""
    pair = f"{user}:{password}".encode("utf-8")
    return "Basic " + base64.b64encode(pair).decode("ascii")


def classify(error):
    """HttpError for a GLib.Error from libsoup or GIO."""
    text = (error.message or "").lower()
    # With TLS 1.3 the server rejects a missing certificate after the
    # handshake, which GnuTLS reports as a received alert, not as
    # CERTIFICATE_REQUIRED.
    if error.matches(Gio.tls_error_quark(), Gio.TlsError.CERTIFICATE_REQUIRED) \
            or "certificate is required" in text:
        return HttpError(CERTIFICATE_REQUIRED,
                         "The server asks for a client certificate")
    if error.domain == GLib.quark_to_string(Gio.tls_error_quark()):
        return HttpError(TLS, f"Secure connection failed: {error.message}")
    # GnuTLS reports a rejected client certificate as a generic alert.
    if "certificate" in text or "tls" in text or "handshake" in text:
        return HttpError(TLS, f"Secure connection failed: {error.message}")
    return HttpError(NETWORK, error.message or "Network error")


def is_certificate_page(body):
    """nginx answers a missing client certificate with HTTP 400 "No
    required SSL certificate was sent" (TLS 1.3 completes the handshake
    first); other proxies use similar pages."""
    text = (body or b"")[:2000].lower()
    return b"ssl certificate" in text or b"client certificate" in text


class Response:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body


class Client:
    """`user_agent` is sent with every request, e.g.
    "MyApp/1.0 (+https://github.com/owner/myapp)"."""

    def __init__(self, user_agent):
        self.user_agent = user_agent
        self._local = threading.local()
        # Read by every thread, replaced by the main thread.
        self.certificate = None
        # Trusted CAs for the server certificate; None is the system's.
        # Tests set their own CA here.
        self.tls_database = None
        # Cookie header per origin (see origin()): the session of a
        # reverse proxy's own login (proxy_login.py). Replaced as a whole.
        self.cookies = {}
        # Authorization header per origin: HTTP Basic auth that a reverse
        # proxy asks for (Pangolin's header authentication,
        # proxy_login.ProxyCredentials). An Authorization header the app
        # sets itself wins. Replaced as a whole.
        self.proxy_auth = {}

    def _session(self):
        session = getattr(self._local, "session", None)
        if session is None:
            session = Soup.Session(user_agent=self.user_agent, timeout=30,
                                   max_conns_per_host=4)
            if self.tls_database is not None:
                session.set_tls_database(self.tls_database)
            self._local.session = session
        return session

    def _message(self, method, url, headers, body, content_type):
        try:
            msg = Soup.Message.new(method, url)
        except TypeError:
            msg = None
        if msg is None:
            raise HttpError(NETWORK, f"Invalid address {_shown(url)}")
        # Redirects are followed by _send(), so that the headers below
        # are set again for each hop's own origin.
        msg.add_flags(Soup.MessageFlags.NO_REDIRECT)
        for name, value in (headers or {}).items():
            msg.props.request_headers.replace(name, value)
        if body is not None:
            msg.set_request_body_from_bytes(content_type,
                                            GLib.Bytes.new(body))
        # Without a certificate libsoup fails the handshake with
        # CERTIFICATE_REQUIRED when the server asks for one, which the
        # connection form turns into "choose your client certificate".
        if self.certificate is not None:
            msg.set_tls_client_certificate(self.certificate)
        key = origin(url)
        cookie = self.cookies.get(key)
        if cookie:
            msg.props.request_headers.replace("Cookie", cookie)
        auth = self.proxy_auth.get(key)
        if auth and not _header(headers or {}, "Authorization"):
            msg.props.request_headers.replace("Authorization", auth)
        return msg

    def request(self, method, url, headers=None, body=None,
                content_type="application/json", timeout=None):
        """Blocking request in the calling (worker) thread."""
        session = self._session()
        if timeout is not None:
            session.props.timeout = timeout
        try:
            msg, data = self._send(session, method, url, headers, body,
                                   content_type, read=True)
        finally:
            if timeout is not None:
                session.props.timeout = 30
        status = msg.get_status()
        response = Response(status, _headers(msg.props.response_headers),
                            data.get_data() or b"")
        if _wants_json(headers) and status < 400 and \
                _header(response.headers, "Content-Type").startswith("text/html"):
            # An API never answers with a web page: a proxy's login page,
            # usually reached through a redirect.
            raise proxy_login(url)
        if status in (400, 403) and is_certificate_page(response.body):
            raise HttpError(CERTIFICATE_REQUIRED,
                            "The server asks for a client certificate", status)
        if status == 401:
            raise HttpError(AUTH, "Signed out by the server", status,
                            challenge=_header(response.headers, "WWW-Authenticate"))
        if status >= 400:
            raise HttpError(SERVER, f"Server error {status}", status)
        return response

    def open(self, method, url, headers=None, body=None,
             content_type="application/x-www-form-urlencoded"):
        """Blocking request that returns (status, headers, input stream)
        before the body is read, for the media proxy."""
        msg, stream = self._send(self._session(), method, url, headers,
                                 body, content_type, read=False)
        return msg.get_status(), _headers(msg.props.response_headers), stream

    def _send(self, session, method, url, headers, body, content_type,
              read):
        """(message, bytes or input stream) of the last hop, following
        redirects (see redirects.py)."""
        for _ in range(redirects.MAX_HOPS + 1):
            msg = self._message(method, url, headers, body, content_type)
            try:
                if read:
                    result = session.send_and_read(msg, None)
                else:
                    result = session.send(msg, None)
            except GLib.Error as e:
                raise classify(e) from None
            location = msg.props.response_headers.get_one("Location")
            hop = redirects.next_hop(method, url, msg.get_status(),
                                     location)
            if hop is None:
                return msg, result
            if not read:
                result.close(None)
            next_method, next_url = hop
            headers = redirects.carried_headers(headers, url, next_url)
            method, url, body = next_method, next_url, None
        raise HttpError(NETWORK, "Too many redirects")


def _wants_json(headers):
    return "json" in (_header(headers or {}, "Accept") or "")


def _header(headers, name):
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return ""


def _headers(soup_headers):
    out = {}
    soup_headers.foreach(lambda name, value: out.__setitem__(name, value))
    return out
