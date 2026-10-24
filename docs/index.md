---
okf_version: "0.2"
---

# Phosh toolkit knowledge bundle

This directory is an [Open Knowledge Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
(OKF v0.2) bundle. One file per concept, YAML frontmatter, plain markdown
links between concepts. Change history is in [log.md](log.md).

# Target platform

* [Device](device.md) - The phone the apps are developed for (placeholder until filled in).
* [Phosh](phosh.md) - The GNOME-based mobile shell the apps run under.

# Guidelines

* [Adaptive libadwaita UI](adaptive-libadwaita.md) - How to build GTK4/libadwaita UIs that work at 360×720 and on the desktop.
* [Screenshot testing](screenshot-testing.md) - How scripts/screenshot.sh renders an app at phone size and its Broadway quirks.

# Workflows

* [Flatpak build and install](flatpak-workflow.md) - Build Flatpak bundles locally and in CI, and install them on the phone.
* [Toolkit usage](toolkit-usage.md) - How an app repository consumes this toolkit.

# Decision records

* [Decisions](decisions/index.md) - Why the toolkit and the app repositories are set up the way they are.
