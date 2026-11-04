---
type: Concept
title: Shared connection and playback
description: The phosh_toolkit Python package that server clients (Ephyra, Nauta) share - HTTP with client certificates, local/remote route with server id check, keyring, connection form, media proxy, playbin player and image cache - and how an app plugs into it.
tags: [shared-code, connection, mtls, tls, networkmanager, keyring, proxy, gstreamer, python]
resource: ../lib/phosh_toolkit/
generated: { by: claude-code/2.1.317, at: 2026-11-04T12:00:00Z }
sources:
  - id: soup-cert
    resource: https://gnome.pages.gitlab.gnome.org/libsoup/libsoup-3.0/method.Message.set_tls_client_certificate.html
    title: libsoup 3, soup_message_set_tls_client_certificate
  - id: nm-dbus
    resource: https://networkmanager.dev/docs/api/latest/spec.html
    title: NetworkManager D-Bus API (ActiveConnections, AccessPoint.Ssid)
---

# Why

The owner runs self-hosted servers that are reachable

- **at home** directly on the LAN, e.g. `http://192.168.1.10:8096`;
- **elsewhere** through a public URL behind a reverse proxy that
  requires a **client certificate** (mutual TLS).

Ephyra (Jellyfin) built the client side for this first; Nauta
(Navidrome) needs the same, so the code moved here
([code reuse](decisions/code-reuse.md)). Pulling it into an app:
[toolkit usage](toolkit-usage.md#3c-shared-python-package).

# Modules

| Module | GTK | What |
|---|---|---|
| `http` | no | `Client(user_agent)`: libsoup 3, one session per worker thread, optional `certificate` and `tls_database`, `open()` streams an answer (also for a `POST` body); errors as `HttpError` with `kind` `network`, `tls`, `certificate-required`, `auth` (401), `server` |
| `tls` | no | `load(data, password)` for PKCS #12 or PEM with key, `describe(cert)` |
| `route` | no | `normalize(text)` (no scheme → `https://`), `candidates(remote, local, home_networks, ssids)`, probe `TIMEOUT` |
| `network` | no | `current_ssids()` from NetworkManager, `Watcher` ("changed", debounced 1.5 s) |
| `router` | no | `Router`: base class of an app's connection (state, `base_url`, `resolve()`, `call()`); `probe_addresses()` for setup |
| `settings` | no | `app_dir(kind, app)` for the XDG directories, `JsonStore(path, cls, version)` for the account file |
| `keyring` | no | `Keyring(schema, labels, memory_env)`: libsecret, memory fallback |
| `certificate` | no | `CertificateFile(path, keyring)`: private copy (mode 600), password in the keyring |
| `proxy` | no | `MediaProxy(forward)`: local HTTP proxy for GStreamer |
| `media` | no | `Media(uri, video=True)`: `playbin3` with a `GtkMediaStream`-like API |
| `tasks` | no | `run(fn, done)`: worker thread, result on the main loop |
| `images` | GDK | `ImageCache(directory, call)`: disk and memory cache of textures |
| `style` | yes | `apply(style)`, `style_row(current, changed)`: Follow System / Light / Dark ([accent decision](decisions/app-accent-colours.md)) |
| `widgets` | yes | `spinner()`, `loading_page()`, `error_page()`, `Ratio` |
| `proxy_login` | yes (WebKitGTK 6) | `make_page()`/`sign_in()`: the proxy's own login in a web view, `CookieJar` for its session cookies |
| `connection_form` | yes | `ConnectionForm`: server address, client certificate, home Wi-Fi groups |
| `testing` | no | `make_pki()`, `server_context()`, `run_until()` for the apps' tests |

Nothing in the package names an app, a server product or a URL.

# Route (`route`, `router`)

The account stores a remote address, an optional local address and a
list of home Wi-Fi names (SSIDs). `route.candidates()` orders them:

| Situation | Tried in order |
|---|---|
| Connected to a listed home Wi-Fi | local, then remote |
| Other Wi-Fi or mobile data | remote only |
| No home list, or NetworkManager not reachable | local, then remote |
| Only one address set | that one |

`Router` asks each candidate who it is with the app's `probe(url,
timeout)` (no credentials; 3 s for the local address, 15 s for the
remote one). The first one that answers **with the server id stored at
sign-in** is used; another server at the same LAN address never gets
the credentials. The route is chosen again when `Gio.NetworkMonitor`
reports a change, and once after a call that failed with a network
error (`Router.call` retries through the new route). A `401` calls the
app's `unauthorized()`.

**Strict mode** (`Router.strict_local = True`, `route.candidates(…,
strict=True)`) is for servers that can't say who they are before the
credentials are sent (Subsonic has no public server id): the local
address is then tried only on a listed home Wi-Fi that NetworkManager
reports, never "everywhere" as a fallback.

An app subclasses `Router` and implements `probe`, `addresses` and
`server_id`; `resolved(kind, url, info)` lets it take the server name
from the probe answer.

**SSID**: read from NetworkManager on the system bus
(`ActiveConnections` → `Type == 802-11-wireless` → `SpecificObject` →
`AccessPoint.Ssid`, falling back to the connection's `Id`)[^nm-dbus].
The Flatpak needs `--system-talk-name=org.freedesktop.NetworkManager`.
Without access the app tries the local address first everywhere, which
the server id check keeps safe.

# Mutual TLS (`tls`, `http`, `certificate`)

- The user picks a **PKCS #12** file (`.p12`/`.pfx`, with password) or a
  **PEM** file with certificate and unencrypted key. The app keeps a
  private copy (mode 600) in its data directory and the PKCS #12
  password in the keyring.
- Loaded with `Gio.TlsCertificate.new_from_pkcs12` / `new_from_pem`; a
  wrong password is `G_TLS_ERROR_BAD_CERTIFICATE_PASSWORD`, shown on the
  password row.
- Every request sets it with `soup_message_set_tls_client_certificate`
  before sending[^soup-cert], so libsoup presents it when the server
  asks, the local address included.
- **Missing certificate**, recognised in three forms: GIO's
  `CERTIFICATE_REQUIRED`; with TLS 1.3 a received alert "Certificate is
  required" (the handshake completes before the server checks); and
  nginx's HTTP 400 page "No required SSL certificate was sent". All
  become `certificate-required`, and the form marks the certificate row.
- The server certificate is checked against the system's CAs; a private
  CA is not supported yet (Ephyra's follow-up issue).

# Proxy login (`proxy_login`)

Many self-hosters put a login of the reverse proxy in front of their
servers (Pangolin's resource authentication, Authelia, Authentik,
oauth2-proxy, …). A browser keeps the proxy's session in a cookie; an app
has none, so the proxy answers instead of the server. Found with the
owner's Jellyfin on 2026-11-04: mutual TLS completed, then the public
`/System/Info/Public` answered `401`, `text/plain`, `Unauthorized`; with
the proxy login switched off everything worked (nexumia-de/phosh-toolkit#28).

- **Detection** (`http`, `router`): a web page where JSON was asked for
  (`Accept: application/json`, the usual redirect to a login page), or a
  `401`/`403` on the probe, which needs no credentials, so only a proxy
  refuses it, becomes `HttpError` kind `proxy-login` with the address to
  open. A `401` on any other call is checked with the probe: if the probe
  is refused too, the proxy's session ran out (signal `proxy-login`, no
  sign-out); if the probe answers, the server rejected the credentials
  (`unauthorized()`).
- **Login** (`make_page`, `sign_in`): an `AdwNavigationPage` with a
  WebKitGTK 6 web view in an ephemeral network session opens the
  address. WebKit's client-certificate request is answered with the app's
  certificate, so mutual TLS works there too. After each page load the
  cookies for the server's origin are tried with the app's probe in a
  separate client; once the server answers, the page reports them.
- **Session**: `CookieJar` keeps `{origin: "name=value; …"}` in the app's
  keyring (kind `proxy-cookies`); `http.Client.cookies` sends them only to
  that origin, also for the media proxy's upstream requests.
- The connection form shows the login page when its check meets a proxy
  login and checks again afterwards; `apply()` stores the cookies. Apps
  connect the router's `proxy-login` signal to `sign_in()`, so an expired
  session opens the login page again.
- Not covered yet: HTTP Basic auth at the proxy (WebKit's own dialog
  appears in the login page, but the app's requests don't send it) and
  static access-token headers.

WebKitGTK 6 is part of `org.gnome.Platform//51` (`WebKit-6.0.typelib`,
checked in the local runtime); on Ubuntu hosts `gir1.2-webkit-6.0`.
Outside Flatpak WebKit sandboxes its web processes with bubblewrap and
aborts the whole process if that fails; GitHub's Ubuntu 24.04 runners
restrict the user namespaces it needs (AppArmor), so the two web-view
tests skip there (`testing.webkit_sandbox_works()`) and run where the
sandbox works, e.g. in the cloud dev container. The rest of the proxy
login is tested everywhere.

# Connection form (`connection_form`)

`ConnectionForm` builds the "Server" group (address, client certificate,
certificate password) and the "Home Network" group (local address, home
Wi-Fi list with "Add Current Wi-Fi"). Apps use it on their first-run
page and in the preferences. `check(done)` validates the addresses,
loads the certificate and probes both addresses; `apply(account)`
writes the addresses and keeps or deletes the certificate. The account
object needs `remote_url`, `local_url`, `home_networks` and
`certificate`.

# Media proxy and player (`proxy`, `media`)

GStreamer's HTTP source and HLS downloader can't present a client
certificate, and credentials must not sit in the URLs the player sees.
The player opens `http://127.0.0.1:<port>/<secret>/<server path>`:

- a `ThreadingHTTPServer` on 127.0.0.1, random port, random path secret
  (other local programs can't use it);
- the app's `forward(path)` returns the client, the upstream URL on the
  current route and the headers, so each app adds its own credentials
  (Jellyfin: `Authorization` header). A fourth item, a form body, sends
  the request up as `POST` with the credentials in the body (Subsonic's
  OpenSubsonic `formPost`), so they appear in no URL and no proxy log;
- `Range` and `If-Range` pass through (seeking), `Accept-Encoding:
  identity` keeps lengths right; without a length the answer ends by
  closing.

`Media` plays the proxy URL with `playbin3`. `Gtk.MediaFile` can't be
used in GTK 4.20 (GNOME 51): its GStreamer backend reads the URI through
GIO, and the Flatpak has no gvfs for `http://` (found with Ephyra on the
phone, 2026-11-04). `video=False` plays sound only.

# Security notes

- At home the local address is often plain HTTP: credentials cross the
  home Wi-Fi unencrypted. Use an `https` local address if that matters.
- A Wi-Fi with the same name elsewhere makes the app try the local
  address there; a stranger's server fails the server id check, but one
  that fakes the public server answer could still receive credentials.
  Prefer an `https` local address, or leave the home list empty.

# Verified (2026-11-04, cloud container, Ubuntu 24.04, libsoup 3.4.4, GLib 2.80, GStreamer 1.24)

`tests/lib/`: the client over real mutual TLS against a Python server
with certificates made by `openssl` (refused without, works with PKCS #12
and PEM), the nginx page, the route at home, away, with the local
server down and with a different server, retry after a network error,
401, strict mode, a proxy login (detected, signed in through the
web view over mutual TLS, cookies kept and sent, an expired proxy session
not taken for a server sign-out), the proxy with ranges through mutual TLS and with a
`POST` form body, a WAV played, paused,
seeked and ended through the proxy, the image cache, and the connection
form with real widgets under `xvfb-run`.

[^soup-cert]: libsoup 3, soup_message_set_tls_client_certificate
[^nm-dbus]: NetworkManager D-Bus API
