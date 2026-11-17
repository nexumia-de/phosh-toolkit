---
type: Decision Record
title: The connection form owns the other certificate hosts
description: Hosts besides the server's that the proxy login page may hand the client certificate to are edited in the shared connection form, not in each app's preferences, so the first connect from the setup page works too.
tags: [decision, proxy-login, mutual-tls, connection-form]
generated: { by: claude-code/2.1.326, at: 2026-11-17T06:35:00Z }
sources:
  - "[^issue]: nexumia-de/phosh-toolkit#52"
---

# Status

Accepted (2026-11-17).

# Context

Since #47 the proxy login's web view gives the client certificate only
to the server's host and `certificate_hosts_extra`
([proxy login](../shared-connection.md#proxy-login-proxy_login)).
`ConnectionForm` showed the login page without those hosts, so on the
setup page a login whose identity provider is on another host behind
the same mutual TLS failed[^issue]. Ephyra had added its own row
"Other Hosts for the Certificate" in its preferences (ephyra#34, not
merged) and Nauta needed the same (nauta#45).

Options:

1. A keyword (`certificate_hosts_extra=` list or callable) on
   `ConnectionForm`, each app keeping its own row. Smallest change in
   the toolkit, but the row lives only in the preferences, so the user
   cannot enter the host before the first connect, which is exactly the
   failing case; and both apps would copy the row and its parsing.
2. The form owns the field: an "Other Certificate Hosts" row in the
   server group, read from and written to `account.certificate_hosts`,
   passed to `make_page`. The setup page and the preferences get it
   from the same code.

# Decision

Option 2. It fixes the setup case, removes a row and `parse_hosts`
from each app instead of adding one, and is on by default (shared
behaviour). The row is an expander under the certificate and is shown
only while a certificate is chosen or saved, since without one there is
nothing to hand out. `proxy_login.parse_hosts()` turns the typed text
into host names (moved from Ephyra).

Backward compatible: an account without `certificate_hosts` starts with
an empty field; `apply()` sets the attribute, which an app saves once
its settings have the field. Apps still pass the same list to
`proxy_login.sign_in()` for a session that runs out later.
