---
type: Decision Record
title: Code names for repositories, descriptive names for users
description: Repository and app id keep a short code name; the name users see in the app grid, the metainfo and the About dialog says what the app does. The agent suggests names, the owner chooses.
tags: [decision, naming, metadata]
generated: { by: claude-code/2.1.317, at: 2026-11-04T12:00:00Z }
---

# Status

Accepted (2026-11-04) by the owner, in the discussion about the Matrix
client: code names for repositories, clear names in the Flatpak, and
"you always suggest a few and I decide what they are called".

# Context

The apps were named with Latin and Greek code names (Ephyra, Nauta,
Pulsus, Cirro). They are unique and good search terms, but some are
hard to pronounce and none says what the app does. In Phosh's app grid
only the icon and the name are visible. GNOME solves the same problem
by keeping a code name for the project and the app id and showing a
descriptive name: `org.gnome.Nautilus` is "Files", `org.gnome.Epiphany`
is "Web", `org.gnome.Totem` is "Videos".

# Decision

- **Code name**: repository, app id (`de.nexumia.<CodeName>`), Python
  package and Flatpak manifest use a short, unique code name. The app id
  never changes after the first release.
- **Visible name**: `Name` in the `.desktop` file, `<name>` in the
  metainfo, the window title and the About dialog use a short name that
  says what the app does. It may be fully generic ("Music") or have a
  little character ("Music Stream"); it must not look like the official
  app of a service (no "Jellyfin" or "Navidrome" in the name; the
  description may say what the app works with).
- `GenericName` and `Keywords` in the `.desktop` file carry the
  function words as well, so search finds the app either way.
- **Who names**: for every new app and every renaming the agent suggests
  a few names (code name and visible name, checked against Flathub and
  apps on the phone for collisions) and the owner decides. Agents never
  pick a final name on their own.
- The visible name can change at any time without migration; settings,
  keyring entries and installations are keyed on the app id.

# Consequences

- Existing apps keep their app ids; each gets an issue to choose a
  visible name from the agent's suggestions.
- Two apps with the same generic name ("Music") would sit side by side
  in the app grid; the suggestions say when a name risks that.
- README titles and release texts name both: "Music (Nauta)".
