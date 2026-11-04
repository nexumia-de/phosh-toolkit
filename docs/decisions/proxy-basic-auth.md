---
type: Decision Record
title: HTTP Basic auth at the proxy, kept in the keyring
description: Apps may sign in to a reverse proxy's HTTP Basic auth (Pangolin's header authentication) once and keep user name and password in the keyring, so the proxy login page does not return every session; only for servers that don't use the Authorization header.
tags: [decision, security, proxy-login, pangolin, keyring]
generated: { by: claude-code/2.1.318, at: 2026-11-04T10:30:00Z }
---

# Status

Accepted (2026-11-04), at the owner's request.

# Context

The owner's Pangolin asks for its own login in front of every resource;
the apps show its login page in a web view
([proxy login](../shared-connection.md#proxy-login-proxy_login)). A
resource session lasts 30 days by default and, as far as Pangolin's
source was read, does not renew itself; the
password manager's browser extension does not work in the web view,
and the owner finds logging in again every 30 to 90 days annoying.
Pangolin can instead accept HTTP Basic auth per resource ("header
authentication").

# Decision

- The toolkit supports HTTP Basic auth at the proxy: user name and
  password in the keyring per origin, sent only there
  (`ProxyCredentials`, `Client.proxy_auth`, the form's "Proxy Login").
- An app turns it on (`proxy_basic=True`) only if its server does not
  use the `Authorization` header, because Pangolin passes that header on
  to the server: Nauta (Navidrome, MeTube) yes, Ephyra (Jellyfin) no.
- The web-view login stays for proxies without Basic auth.

# Security trade-off (accepted by the owner)

- Stored, the proxy password is no longer something the user *knows* but
  something the phone *has*: together with the client certificate these
  are two possession factors on one device, not two-factor
  authentication. The second factor against a stolen phone is its lock
  screen.
- A session cookie expires; Basic credentials stay valid until changed.
- Therefore: a user name and password made for the apps only (random,
  kept in the password manager), never a real login; one client
  certificate per device; on a lost device change the credentials in
  Pangolin and block that device's certificate.

# Alternatives

- **Web-view login with long sessions** (`resource_session_length_hours`):
  real "know" factor at each login, but still a login every period.
- **App lock** (certificate password asked at start, never stored): a
  real "know" factor on the device, at the price of typing it.
- **OAuth/OIDC device tokens**: the usual answer for apps behind SSO;
  Pangolin offers nothing like it for resources (as far as its source
  was read).
- **Pangolin access tokens**: they go into URLs, which the apps never do.
