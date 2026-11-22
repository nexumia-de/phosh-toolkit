---
type: Concept
title: Security review of phosh_toolkit (2026-11)
description: Findings of the security review of the shared Python package (issue 45) with severity, fix, test and what apps must adopt - redirects, image cache paths, addresses in the login flow and logs, client certificate hosts, account file mode, keyring fallback.
tags: [security, review, shared-code, connection, mtls, proxy, keyring]
resource: ../lib/phosh_toolkit/
generated: { by: claude-code/2.1.330, at: 2026-11-21T12:00:00Z }
sources:
  - id: issue-45
    resource: https://github.com/nexumia-de/phosh-toolkit/issues/45
    title: Security review of phosh_toolkit (issue 45, 2026-11-08)
  - id: pr-47
    resource: https://github.com/nexumia-de/phosh-toolkit/pull/47
    title: Fix security review findings 1-4 in phosh_toolkit (pull request 47)
---

# Scope

All modules of `lib/phosh_toolkit/`
([shared connection](shared-connection.md)), reviewed on 2026-11-08
(issue 45[^issue-45]) and again on 2026-11-21 against `main` after the
first fixes[^pr-47]. Apps affected: Ephyra and Nauta (all connection
modules), Pulsus (`settings` only).

# Findings

| # | Severity | Finding | Fix | Test |
|---|---|---|---|---|
| 1 | Medium | The proxy session cookie, set as a raw `Cookie` header, followed a redirect to another host (libsoup 3.4.4 keeps raw headers) | `http.Client` follows redirects itself; cookie, proxy Basic auth and the app's headers are scoped per origin, only an allow-list crosses origins, a body is never resent ([redirects](shared-connection.md#redirects-redirects-http)) | `tests/lib/test_redirects.py` |
| 2 | Medium | `ImageCache` wrote to `directory / name` with names built from server data: `..` or an absolute path wrote outside the cache | Files are named after the SHA-256 of the key; files with old names are removed at start | `test_widgets.py` |
| 3 | Medium-low | The proxy-login error and web view carried the full request URL with its query; the web view gave the client certificate to any host | `HttpError.url` is `page_url()`; the web view opens `start_url()`; the certificate goes to the server's host and `certificate_hosts_extra` only | `test_proxy_login.py` |
| 4 | Medium-low | The media proxy logged its path secret | `redact()` on its request log, error lines and `Media`'s log lines | `test_connection.py`, `test_media.py` |
| 5a | Low | `route.normalize` accepted user info (`https://user:pw@host`), which was then saved in the account file and sent | Refused with an `AddressError` that does not repeat the address | `test_normalize_rejects_user_info` |
| 5b | Low | The account file was written with the default umask (world-readable; addresses and user names, no secrets) | `JsonStore` writes mode 600 and tightens an existing file when it reads it | `test_account_file_is_private` |
| 5c | Low | Full URLs in error texts and the proxy's 502 answer | `Invalid address` shows `page_url()`; the 502 body is redacted | `test_proxy_502_body_has_no_secret_and_no_query` |
| 5d | Low | Proxy credentials stayed in the keyring when the remote address was cleared | `ConnectionForm.apply()` forgets credentials and session cookies of every origin that is no longer an address of the account | `test_proxy_basic_fields` |
| 5e | Low | A failed keyring store left a copy in memory that shadowed every later value | A store the keyring takes drops the copy | `test_keyring_copy_in_memory_goes_when_the_keyring_works_again` |
| 7 | Low | Found on 2026-11-21: `http.Client` set the client certificate on every redirect hop, so any answer (also from a plain `http` local address on a strange network) could make the app identify itself to a host of its choosing; the same flaw as in the web view (3) | The certificate goes to the host the app asked and to `Client.certificate_hosts` only ([mutual TLS](shared-connection.md#mutual-tls-tls-http-certificate)) | `test_client_certificate_stays_with_the_requested_host` |
| 8 | Info | Found on 2026-11-21: the media proxy compared its secret with `startswith` | `hmac.compare_digest` | covered by the proxy tests |

# Decided, no change

- **5a, `http://` for the remote address** stays accepted, without a
  warning: an address without scheme becomes `https://`, so plain HTTP
  is the user's explicit choice, and the app cannot tell a VPN address
  from the open internet. Decided on 2026-11-22:
  [http remote address](decisions/http-remote-address.md).
- **6, information**: errors are classified by server text, and strict
  mode trusts the Wi-Fi name alone. Both are recorded in the
  [security notes](shared-connection.md#security-notes); no change.
- Each player connection through the media proxy does a fresh mutual
  TLS handshake: performance, not security.

# Checked and fine

Server certificate validation, the 0600 certificate copy, the server id
check in the route switch, the response header whitelist of the media
proxy, the per-app keyring schema.

# What apps adopt with the pin bump

- Set `http.certificate_hosts` (finding 7) when a redirect may lead
  from one address of the server to the other or to an identity
  provider behind the same mutual TLS:
  `proxy_login.certificate_hosts(remote, extra) | proxy_login.certificate_hosts(local)`.
  Without it such a redirect ends as `proxy-login`.
- An address with user info is now an `AddressError` in the form.
- `ConnectionForm.apply()` removes proxy cookies and credentials of
  origins that are no longer configured; reload `http.cookies` and
  `http.proxy_auth` from the keyring after it, as before.
- The media proxy's 502 has the reason "Bad Gateway"; the redacted
  message is in the body.
- Pass `certificate_hosts_extra` (finding 3), as asked in
  nexumia-de/ephyra#33 and nexumia-de/nauta#45.

[^issue-45]: Security review of phosh_toolkit (issue 45)
[^pr-47]: Fix security review findings 1-4 in phosh_toolkit (pull request 47)
