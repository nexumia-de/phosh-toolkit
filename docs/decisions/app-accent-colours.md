---
type: Decision Record
title: One accent colour per app, style chosen by the user
description: Each app has its own accent colour instead of the system accent; light and dark follow the system unless the user picks one in the app's preferences.
tags: [decision, design, accent, dark-mode]
generated: { by: claude-code/2.1.317, at: 2026-11-03T23:45:00Z }
---

# Status

Accepted (2026-11-03) by the owner: "different colour for each app and
dark/light based on system or user selectable". Supersedes the rules
"do not override the accent colour" and "offer a style switch only for
apps used for long periods" in [visual design](../design.md).

# Context

The owner wants all apps to look clean and modern, like Ephyra's
Jellyfin look, not only Ephyra. Stock libadwaita already looks clean;
what the apps lacked was identity: every app had the same system accent,
and dark mode only came from the system setting, which Phosh users
rarely change per app.

# Decision

- Each app picks **one accent colour** and sets only
  `--accent-bg-color` and `--accent-fg-color` in its `style.css`. All
  other colours stay libadwaita's.
- Light and dark **follow the system** by default; each app's
  preferences have a "Style" row with Follow System / Light / Dark,
  kept across starts. High contrast always follows the system.

# Consequences

- Apps are recognisable at a glance and still consistent with each
  other and with Phosh.
- The user's system accent colour is ignored inside these apps.
- The style row moved into the toolkit (`phosh_toolkit.style`) when
  Nauta became its second app after Ephyra (2026-11-04).
- libadwaita 1.5 hosts (Ubuntu 24.04) don't parse the CSS variables;
  apps may repeat the accent as `@define-color accent_bg_color` for host
  screenshots.
