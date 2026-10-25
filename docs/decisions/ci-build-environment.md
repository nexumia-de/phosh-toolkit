---
type: Decision Record
title: Flatpak CI on plain Ubuntu runners, not Flathub's build container
description: The reusable Flatpak workflow keeps installing flatpak-builder from apt on ubuntu-24.04 runners instead of running in ghcr.io/flathub-infra/flatpak-github-actions; measured build times give the container little to win, and the screenshot step depends on Ubuntu.
tags: [decision, ci, flatpak, github-actions]
generated: { by: claude-code/2.1.310, at: 2026-10-25T20:00:00Z }
sources:
  - id: fga
    resource: https://github.com/flathub-infra/flatpak-github-actions
    title: flatpak-github-actions README
  - id: pw-deps
    resource: https://playwright.dev/docs/browsers#install-system-dependencies
    title: Playwright docs, installing system dependencies
---

# Status

Accepted (2026-10-25). The switch was proposed as a best practice and
then rejected after measuring.

# Context

Flathub's `flatpak-github-actions` offers container images with
flatpak-builder and a preinstalled runtime, e.g. a GNOME image.[^fga]
The motivation was one slow run on 2026-10-24 (apt fetched 166 MB at
144 kB/s, 19 minutes).

# Decision

Stay on `ubuntu-24.04` and `ubuntu-24.04-arm` with apt-installed
flatpak-builder.

- Measured on 2026-10-25: Cirro's x86_64 build including the eight
  screenshots took 3.5 minutes, aarch64 about 2 minutes, the demo app
  1–2.5 minutes. The container could save the runtime download, a
  fraction of that.
- The screenshot step needs `gtk4-broadwayd`, D-Bus tools and
  Playwright's `install --with-deps`, which supports Debian and Ubuntu
  only.[^pw-deps] The images are Fedora-based, so the step would need a
  second implementation.
- The slow-mirror case is already bounded by the 30-minute job timeout
  and apt's lock timeout.

# Consequences

- Reconsider if apt or Flathub downloads make builds regularly slower
  than about 10 minutes, or if a container gains the screenshot
  dependencies.
