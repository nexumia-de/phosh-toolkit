"""Signing in to a reverse proxy's own login (SSO) in front of the server
(phosh-toolkit docs/shared-connection.md).

Some proxies (Pangolin, Authelia, Authentik, oauth2-proxy, …) ask for
their own login before they pass anything to the server; browsers keep the
proxy's session in a cookie. The app shows the proxy's login page in a web
view (WebKitGTK 6, with the client certificate for mutual TLS), takes the
cookies the proxy set once the server answers through it, keeps them in
the keyring and sends them with every request (http.Client.cookies)."""
import json
import logging

import gi

from phosh_toolkit import tasks
from phosh_toolkit.http import Client, HttpError, origin

log = logging.getLogger("phosh_toolkit.proxy_login")

# Keyring kind of the stored cookies: {origin: "name=value; …"}.
COOKIES = "proxy-cookies"


class CookieJar:
    """The proxy cookies of every origin, in the app's keyring."""

    def __init__(self, keyring):
        self.keyring = keyring

    def load(self):
        try:
            return json.loads(self.keyring.lookup(COOKIES) or "{}")
        except ValueError:
            return {}

    def save(self, cookies):
        if cookies:
            self.keyring.store(COOKIES, json.dumps(cookies))
        else:
            self.keyring.clear(COOKIES)


def cookie_header(cookies):
    """"a=1; b=2" from Soup.Cookie objects."""
    return "; ".join(f"{c.get_name()}={c.get_value()}" for c in cookies)


def available():
    """WebKitGTK 6 can be loaded (it is in the GNOME runtime)."""
    try:
        gi.require_version("WebKit", "6.0")
        from gi.repository import WebKit  # noqa: F401
    except (ImportError, ValueError):
        return False
    return True


def make_page(server_url, login_url, http, probe, done, trusted=()):
    """An Adw.NavigationPage with the proxy's login page.

    - server_url: the server's base address (the route's base URL).
    - login_url: what to open, usually the address the proxy refused.
    - http: the app's http.Client (client certificate, cookies).
    - probe(http, url, timeout): the app's probe through the given
      http.Client (see router.Router.probe).
    - done(cookies): on the main loop once the server answers through the
      proxy; `cookies` is the Cookie header for server_url's origin. The
      caller stores it (CookieJar) and pops the page.
    - trusted: (Gio.TlsCertificate, host) pairs the web view accepts
      besides the system's CAs (tests with their own CA)."""
    gi.require_version("WebKit", "6.0")
    from gi.repository import Adw, Gtk, WebKit

    page = Adw.NavigationPage(title="Sign In to the Proxy", tag="proxy-login")
    session = WebKit.NetworkSession.new_ephemeral()
    for certificate, host in trusted:
        session.allow_tls_certificate_for_host(certificate, host)
    view = WebKit.WebView(network_session=session, vexpand=True)
    key = origin(server_url)
    state = {"checking": False, "finished": False}
    page.view = view

    def on_authenticate(view, request):
        if request.get_scheme() != WebKit.AuthenticationScheme.CLIENT_CERTIFICATE_REQUESTED:
            return False    # basic auth and others: WebKit's own dialog
        if http.certificate is None:
            request.cancel()
        else:
            request.authenticate(WebKit.Credential.new_for_certificate(
                http.certificate, WebKit.CredentialPersistence.FOR_SESSION))
        return True

    def on_load(view, event):
        if event == WebKit.LoadEvent.FINISHED and not state["finished"]:
            session.get_cookie_manager().get_cookies(
                server_url, None, on_cookies)

    def on_cookies(manager, result):
        try:
            cookies = cookie_header(manager.get_cookies_finish(result))
        except Exception as e:   # GLib.Error
            log.info("cookies: %s", e)
            return
        if not cookies or state["checking"] or state["finished"]:
            return
        state["checking"] = True
        # A separate client, so the app's requests don't see untested
        # cookies.
        trial = Client(http.user_agent)
        trial.certificate = http.certificate
        trial.tls_database = http.tls_database
        trial.cookies = dict(http.cookies, **{key: cookies})

        def check():
            # Does the server answer through the proxy with these cookies?
            probe(trial, server_url, 15)

        def checked(result, error):
            state["checking"] = False
            if error is None:
                state["finished"] = True
                done(cookies)
            elif not isinstance(error, HttpError):
                log.warning("proxy login check: %s", error)

        tasks.run(check, checked)

    view.connect("authenticate", on_authenticate)
    view.connect("load-changed", on_load)
    toolbar = Adw.ToolbarView(content=view)
    header = Adw.HeaderBar()
    reload_button = Gtk.Button(icon_name="view-refresh-symbolic",
                               tooltip_text="Reload")
    reload_button.update_property([Gtk.AccessibleProperty.LABEL], ["Reload"])
    reload_button.connect("clicked", lambda *_: view.reload())
    header.pack_end(reload_button)
    toolbar.add_top_bar(header)
    page.set_child(toolbar)
    view.load_uri(login_url or server_url)
    return page


def sign_in(nav, router, http, jar, probe, url="", trusted=(), done=None):
    """Push the login page onto `nav` (an Adw.NavigationView) for the
    router's current or first address; on success store the cookies in
    `jar`, resolve the route again and call done(). `probe(http, url,
    timeout)` as in make_page(). Does nothing while the
    page is already shown or WebKitGTK is missing (then the error stays
    visible)."""
    visible = nav.get_visible_page()
    if visible is not None and visible.get_tag() == "proxy-login":
        return None
    if not available():
        log.warning("WebKitGTK 6 is missing; can't show the proxy login")
        return None
    server = router.base_url or _first_address(router)
    if not server:
        return None

    def finished(cookies):
        stored = jar.load()
        stored[origin(server)] = cookies
        jar.save(stored)
        http.cookies = dict(http.cookies, **{origin(server): cookies})
        nav.pop()
        router.resolve()
        if done:
            done()

    page = make_page(server, url or server, http, probe, finished, trusted)
    nav.push(page)
    return page


def _first_address(router):
    remote, local, _ = router.addresses()
    return remote or local
