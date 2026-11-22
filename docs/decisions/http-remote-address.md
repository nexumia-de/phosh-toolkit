---
type: Decision Record
title: A typed http:// remote address stays allowed, without a warning
description: The connection form keeps accepting an explicit http:// for the remote address and shows no warning; an address without scheme becomes https://. Closes the open point of the 2026-11 security review.
tags: [decision, security, connection, connection-form]
generated: { by: claude-code/2.1.330, at: 2026-11-22T12:00:00Z }
---

# Status

Accepted (2026-11-22). Decided by the agent while closing issue 45; the
security review had left it to the owner, who asked for the open
issues to be decided by best practice.

# Context

`route.normalize()` turns an address without scheme into `https://`, so
plain HTTP to the remote address only happens when the user types
`http://`. The [security review](../security-review.md) (finding 5a)
asked whether that should be refused or warned about: over the open
internet, a token or password sent to an `http://` address can be read
on the way.

The app cannot tell the open internet from a private network. The
"remote" address is often a VPN or mesh address (WireGuard, Tailscale),
where the tunnel encrypts and the server speaks plain HTTP; the same
form field serves both.

# Decision

Keep accepting a typed `http://` for the remote address, and show no
warning.

- Refusing would lock out the VPN set-ups the route logic was built
  for, with no way for the app to tell them apart.
- A warning would be wrong for those users every time they open the
  form, and a warning that is usually wrong teaches people to ignore
  warnings. The form has no place for per-row hints either; it marks
  rows only on errors.
- The safe default is already in place: no scheme means `https://`,
  certificates are validated, and user info in an address is refused.

# Consequences

- Nothing changes in the code or for the apps.
- The security notes say that `http://` is the user's explicit choice
  and safe only inside a tunnel or at home.
- If an app ever gets users beyond the owner who mistype `http://` for
  a public server, a one-time hint on save is the smallest next step;
  that would be a new issue with that evidence.
