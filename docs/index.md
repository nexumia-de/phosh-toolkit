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
* [Visual design](design.md) - Stock libadwaita styling, colour, typography, icons, text and feedback patterns, with a review checklist.
* [Screenshot testing](screenshot-testing.md) - How scripts/screenshot.sh renders an app at phone size and its Broadway quirks.

# Workflows

* [Host setup](host-setup.md) - What setup.sh installs (full and ci profiles), why cage replaced weston, and the apt hardening.
* [Flatpak build and install](flatpak-workflow.md) - Build Flatpak bundles locally and in CI, and install them on the phone.
* [Shared app repository](app-repository.md) - Publish all apps as one Flatpak repository that GNOME Software on the phone installs and updates from.
* [Dependency updates](dependency-updates.md) - Pinned versions kept current by the update-check workflow (Flatpak modules, GNOME runtime) and Dependabot (GitHub Actions).
* [Licensing](licensing.md) - REUSE for own files, licence inventory, licence texts and source bundles for bundled code, data attribution.
* [Branch protection](branch-protection.md) - Ruleset files that keep main behind pull requests with green CI, and how to import them.
* [Toolkit usage](toolkit-usage.md) - How an app repository consumes this toolkit.

# Decision records

* [Decisions](decisions/index.md) - Why the toolkit and the app repositories are set up the way they are.
