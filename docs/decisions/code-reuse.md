---
type: Decision Record
title: Code reuse between apps
description: When and how code shared by several apps moves into phosh-toolkit, and how apps consume it without copy-paste.
tags: [decision, reuse, toolkit, flatpak]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
---

# Status

Accepted (2026-10-25).

# Context

With [one repository per app](one-repo-per-app.md), the same helpers
(HTTP client with `User-Agent` and cache, style loading, about dialog,
status pages) tend to be copied from app to app and then drift apart.
Extracting too early has the opposite cost: a shared API shaped by one app
that the next app has to work around. Setup, rules, scripts and CI are
already shared through the [central toolkit](central-toolkit.md); app
runtime code is not yet.

# Decision

1. **Rule of three.** Code stays in the app until a second app needs it.
   The second app does not copy it: the code moves into the toolkit and
   both apps use it from there. Code written for one app only is not
   generalised in advance.
2. **Shared runtime code lives in phosh-toolkit as one Python package**
   (planned path `lib/phosh_toolkit/`, created with the first shared
   module). It is small, has no dependencies beyond PyGObject, GTK 4 and
   libadwaita, and contains no app-specific names or URLs.
3. **Apps consume it as a Flatpak module pinned to a toolkit tag**
   (`type: git`, `tag:` plus `commit:`), never `main`, so a toolkit change
   cannot break an app build unannounced. Bumping the tag is a normal app
   change.
4. **Patterns that are not code** (how a view is built, which widget to
   use) go into [visual design](../design.md) or
   [adaptive libadwaita UI](../adaptive-libadwaita.md), not into a library.
5. **Boilerplate for new apps** (window, `main.py`, meson, metainfo,
   `.desktop`, manifest, CI workflow, `AGENTS.md`) comes from the demo app
   in `examples/`, which is kept as the reference skeleton and updated when
   the conventions change.

# Consequences

- Duplicated code between two apps is a defect to fix, not a style choice.
- The first extraction has to create the package and its Flatpak module
  snippet; document both in [toolkit usage](../toolkit-usage.md) then.
- Shared modules need their own tests in the toolkit, because a bug
  reaches every app that bumps the tag.
