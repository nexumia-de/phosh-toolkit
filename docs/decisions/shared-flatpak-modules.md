---
type: Decision Record
title: Shared Flatpak modules through a git submodule; the map set-up stays in the apps
description: The libshumate and protobuf-c manifest modules live in phosh-toolkit's flatpak/ and apps include them through the toolkit as a git submodule; the location wrapper moved into phosh_toolkit, the map set-up did not.
tags: [decision, flatpak, shared-code, libshumate, location]
generated: { by: claude-code/2.1.330, at: 2026-11-22T12:00:00Z }
---

# Status

Accepted (2026-11-22). Decided by the agent while closing issue 22; the
owner had asked for all open issues to be decided by best practice.

# Context

Vestigia is the second app after Cirro that needs the own location and
a libshumate map ([code reuse](code-reuse.md): code moves here when a
second app needs it). Issue 22 asked for three things: the location
wrapper, the two manifest modules "as a shared snippet that apps
include, instead of copying them", and the map set-up "only if it is
still identical in both apps once Vestigia's map exists".

flatpak-builder resolves a module file relative to the manifest; it
cannot fetch one from another repository. Checked with flatpak-builder
1.4.2: `--show-manifest` inlines an included file, also from `../`.

# Decision

1. `phosh_toolkit.location` is Cirro's wrapper with the distance
   threshold as a required argument.
2. The modules are one file, `flatpak/libshumate.yml` (libshumate with
   protobuf-c nested). Apps add phosh-toolkit as a **git submodule** and
   list `toolkit/flatpak/libshumate.yml`; the submodule points to the
   tag the app's `phosh-toolkit` module pins.
3. The toolkit's demo manifest includes the file, so the self-test
   builds it on both architectures, and the toolkit's own update check
   keeps the versions current.
4. The **map set-up is not moved**. Vestigia has no map code yet
   (2026-11-22), so there is nothing to compare; it is six lines of
   libshumate calls around app-specific values (user agent, layers).
   If both apps end up with the same lines, moving them is a new issue.

# Alternatives

- **Each app keeps its own copy of the two modules**, updated by its
  own update check. Least machinery, but a build fix has to be made per
  app, and it is what the issue set out to end.
- **The workflow places the toolkit next to the app** and the manifest
  includes `../phosh-toolkit/flatpak/…`. One pin less, but local
  builds, the update check and every other tool would need the same
  layout, and the manifest would not build from a plain clone.
- **A script that copies the snippet into the app** with a drift check
  in CI. More code than the problem.

# Consequences

- Apps with a map carry two toolkit pins (submodule, `phosh-toolkit`
  module) that must change together; the usage page says so.
- The toolkit's CI builds libshumate; the flatpak-builder cache keeps
  the cost to the first run after a version change.
- The toolkit has its own `docs/dependencies.md`.
