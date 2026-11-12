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
  - id: pangolin-header
    resource: https://github.com/fosrl/pangolin/blob/9af8dad/server/routers/badger/verifySession.ts
    title: Pangolin, verifySession (header auth, headerAuthChallenged), commit 9af8dad (2026-11-02)
  - id: badger
    resource: https://github.com/fosrl/badger/blob/2b781d2/main.go
    title: Pangolin's Traefik plugin Badger, main.go, commit 2b781d2 (2026-10-21)
  - id: jellyfin-auth
    resource: https://github.com/jellyfin/jellyfin/blob/804eb74/Jellyfin.Server.Implementations/Security/AuthorizationContext.cs
    title: Jellyfin, AuthorizationContext (GetAuthorizationDictionary), commit 804eb74 (2026-11-03)
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

# Used by

| App | Modules |
|---|---|
| [Ephyra](https://github.com/nexumia-de/ephyra) (Jellyfin) | all except `testing` in the app (tests use it); `network` through `router`; `proxy_basic` off |
| [Nauta](https://github.com/nexumia-de/nauta) (Navidrome, MeTube) | all except `testing` in the app (tests use it); `network` through `router`; `proxy_basic` on |
| [Pulsus](https://github.com/nexumia-de/pulsus) (Amazfish's data, display only) | `settings`, `style` |

A change to a module is adopted in every app listed for it, in the same
task (`AGENTS.md`, "Shared code"). Keep this table current.

# Modules

| Module | GTK | What |
|---|---|---|
| `http` | no | `Client(user_agent)`: libsoup 3, one session per worker thread, optional `certificate` and `tls_database`, `open()` streams an answer (also for a `POST` body); errors as `HttpError` with `kind` `network`, `tls`, `certificate-required`, `auth` (401), `server` |
| `redirects` | no | Redirect rules of `http.Client` (`next_hop`, `carried_headers`) and `origin(url)`, the key of the per-origin headers |
| `tls` | no | `load(data, password)` for PKCS #12 or PEM with key, `describe(cert)` |
| `route` | no | `normalize(text)` (no scheme → `https://`), `candidates(remote, local, home_networks, ssids)`, probe `TIMEOUT` |
| `network` | no | `current_ssids()` from NetworkManager, `Watcher` ("changed", debounced 1.5 s, from GLib's network monitor and NetworkManager's signals) |
| `router` | no | `Router`: base class of an app's connection (state, `base_url`, `resolve()`, `call()`); `probe_addresses()` for setup |
| `settings` | no | `app_dir(kind, app)` for the XDG directories, `JsonStore(path, cls, version)` for the account file |
| `keyring` | no | `Keyring(schema, labels, memory_env)`: libsecret, memory fallback |
| `certificate` | no | `CertificateFile(path, keyring)`: private copy (mode 600), password in the keyring |
| `proxy` | no | `MediaProxy(forward)`: local HTTP proxy for GStreamer |
| `media` | no | `Media(uri, video=True, audio_position=None)`: `playbin3` with a `GtkMediaStream`-like API, audio track choice, no subtitles |
| `tasks` | no | `run(fn, done)`: worker thread, result on the main loop |
| `images` | GDK | `ImageCache(directory, call)`: disk and memory cache of textures; files are named after the SHA-256 of the key, so a key built from server data never chooses the path |
| `style` | yes | `apply(style)`, `style_row(current, changed)`: Follow System / Light / Dark ([accent decision](decisions/app-accent-colours.md)) |
| `widgets` | yes | `spinner()`, `loading_page()`, `error_page()`, `Ratio` |
| `proxy_login` | yes (WebKitGTK 6) | `make_page()`/`sign_in()`: the proxy's own login in a web view, `CookieJar` for its session cookies, `ProxyCredentials` for its HTTP Basic auth |
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
the credentials. The route is chosen again when the network changes,
and once after a call that failed with a network error (`Router.call`
retries through the new route). A `401` calls the app's
`unauthorized()`.

**Switching while the app runs** (the owner: "app running, Wi-Fi gone,
it stays on the local address", 2026-11-04). Three gaps, closed:

- `network.Watcher` listened only to `Gio.NetworkMonitor`. In the
  Flatpak that is the network portal, which reports what the host's
  monitor reports and may say nothing while the network stays
  "available" (Wi-Fi to mobile data). The watcher now also subscribes
  to NetworkManager's `PropertiesChanged` on its root object
  (`ActiveConnections`, `PrimaryConnection`, `State`, `Connectivity`),
  which the app may already talk to (`--system-talk-name`).
- Leaving a Wi-Fi comes as several changes; the first search can still
  see the home Wi-Fi (and reach the local address). A `resolve()` while
  a search runs used to be dropped; now the router searches once more
  when the first search ends, and the waiting callbacks get that
  answer.
- A song already streaming kept its connection to the old address until
  a 30 s timeout. `MediaProxy.follow(router)` cuts the running upstream
  reads when the router moves to another address (`reroute()`);
  GStreamer's HTTP source then reconnects with a `Range` from where it
  was and gets the new address from `forward()`. Tested with real
  GStreamer (`tests/lib/test_media.py`).

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

# Redirects (`redirects`, `http`)

`http.Client` follows redirects itself (`SOUP_MESSAGE_NO_REDIRECT`), up
to 20 hops, because libsoup keeps raw request headers on a redirect to
another host: the proxy cookie set as a `Cookie` header went along to
the new host (reproduced with libsoup 3.4.4, issue
nexumia-de/phosh-toolkit#45). For each hop:

- `cookies` and `proxy_auth` are looked up again for the hop's origin,
  so they reach only their own origin;
- the app's own headers stay within one origin; across origins
  `Authorization`, `Cookie`, `Proxy-Authorization` and Jellyfin's
  `X-Emby-*`/`X-MediaBrowser-Token` are dropped;
- 301/302 after a `POST` and every 303 continue as `GET` without body;
  a 307/308 that would resend a body is handed to the caller unfollowed
  (as libsoup did), so a form body with a password never reaches a
  redirect target;
- a `Location` that is not `http(s)` is handed to the caller.

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
- Not covered yet: static access-token headers (Pangolin's access
  tokens go into URLs, which the apps never do).

## HTTP Basic auth at the proxy (`ProxyCredentials`)

A login page every 30 days (Pangolin's default `resource_session_length_hours`
720) is too often for the owner, so a proxy that takes HTTP Basic auth
can be signed in once for good
([decision](decisions/proxy-basic-auth.md)). Pangolin calls this
"header authentication" (per resource: user name and password, stored as
a hash)[^pangolin-header]:

- **Pangolin**: a valid `Authorization: Basic …` header lets the request
  through without a session, alongside Platform SSO (browsers keep
  their SSO login). With "extended compatibility" a request without it
  gets `401` with `WWW-Authenticate: Basic realm="pangolin"`, but **only
  when Platform SSO is off**; with SSO on (the owner's setup) it gets the
  usual redirect to the login page, so the app shows the web view and the
  user opens "Proxy Login" by hand. Set in a resource policy, header
  auth replaces the resources' own: one pair for every resource of that
  policy (`effectivePolicyHeaderAuth ?? resourceHeaderAuth`); separate
  pairs need separate policies. Pangolin's mTLS ("Client Certificate
  (mTLS)") is a Traefik TLS option (`clientAuthType:
  RequireAndVerifyClientCert` with the policy's CAs), checked in the
  handshake before and in addition to these methods. Pangolin's Traefik
  plugin Badger **passes the `Authorization` header on to the server**
  (it removes only its own headers and session cookie)[^badger].
- **So the server must not use `Authorization` itself.** Navidrome's
  Subsonic API and MeTube don't (Nauta: credentials in the body). Jellyfin
  does: it reads its token from `Authorization` and looks at
  `X-Emby-Authorization`/`X-Emby-Token` only when that header is empty
  **and** "EnableLegacyAuthorization" is on (off by default)[^jellyfin-auth].
  Ephyra therefore does not offer it.
- `http.Client.proxy_auth` is `{origin: "Basic …"}` like `cookies`: sent
  only to that origin (the remote address), also for the media proxy;
  an `Authorization` header the app sets itself wins.
- `HttpError.challenge` keeps a 401's `WWW-Authenticate`;
  `wants_basic` is true for Basic. The router keeps the last proxy-login
  error in `proxy_error`; `proxy_login.sign_in(…, on_basic=…)` opens no
  web page for a Basic challenge (WebKit would only show its own
  dialog) and calls `on_basic()`, so the app points to its form.
- `ProxyCredentials(keyring)` keeps `{origin: {"user", "password"}}` in
  one secret (kind `proxy-credentials`); `headers()` gives
  `Client.proxy_auth`.
- `ConnectionForm(…, proxy_basic=True)` adds the expander row "Proxy
  Login" (user name, password) to the Server group. On a Basic
  challenge it expands, marks both rows and says so; `apply()` keeps the
  credentials for the remote address and forgets those of an old one.

Use a user name and password made for this only (random, from the
password manager), never a real login; on a lost device change them in
Pangolin and block its client certificate.

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
- `reroute()` cancels the running upstream reads; `follow(router)` does
  that whenever the router's address changes. `MediaProxy(connection.forward)`
  follows the router by itself (`forward` is a router method); apps
  need no extra call.

`Media` plays the proxy URL with `playbin3`. `Gtk.MediaFile` can't be
used in GTK 4.20 (GNOME 51): its GStreamer backend reads the URI through
GIO, and the Flatpak has no gvfs for `http://` (found with Ephyra on the
phone, 2026-11-04). `video=False` plays sound only.

- **Tracks**: `Media` answers playbin3's stream collection with a
  `select-streams` event: the first video and the `audio_position`-th
  audio track in file order (None: the first). `select_audio(n)` switches
  while playing, without a restart. No text stream is ever selected:
  playbin3 by itself shows the first embedded subtitle, and a subtitle
  file through its `suburi` made later selections hang ("Still have
  streams to activate", GStreamer 1.28.7; the audio switched in 2 of 8
  runs). Apps that show subtitles draw them (Ephyra).
- `position_now()` reads the position from the pipeline, between the
  250 ms `timestamp` updates.
- `stop()` releases the pipeline and the paintable on the main thread:
  gtk4paintablesink aborts the process when the garbage collector frees
  it on another thread, e.g. one of the proxy's (Ephyra, 2026-11-04).
  After `stop()` the object does nothing more.
- Tested (`tests/lib/test_media.py`): the German of two audio tracks
  plays, no subtitle, switching to English without a restart; stop()
  then a release on another thread.

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
