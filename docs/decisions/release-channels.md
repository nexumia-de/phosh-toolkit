---
type: Decision Record
title: Release channels from main and tags
description: The default branch feeds a nightly app <app id>.Devel, tags v<version> feed the stable app; no long-lived nightly branch.
tags: [decision, flatpak, release, nightly, ci]
generated: { by: claude-code/2.1.310, at: 2026-10-25T16:00:00Z }
---

# Status

Accepted (2026-10-25) by the owner.

# Context

Until now every push to an app's `main` went straight to the phone
through the rolling release `latest`. The owner wants to merge agent
pull requests quickly, try them on the phone, and update the stable app
about once a week. Options:

1. **Trunk and tags**: `main` feeds a separate nightly app
   (`<app id>.Devel`), a tag `v<version>` feeds the stable app.
2. **Option 1 plus a label**: an open pull request with the label
   `nightly` fills the nightly slot instead of `main`, so a pull request
   can be tried before it is merged. One app id means one slot, so the
   workflow has to keep the label unique, fall back to `main` on merge,
   close or unlabel, and drop stale uploads.
3. **A long-lived `nightly` branch**: pull requests target `nightly`,
   the owner merges `nightly` into `main` weekly.

# Decision

Option 1. It is how GNOME apps ship (GNOME Nightly from `main`, Flathub
from tags) and gives the weekly cadence with one command, a tag. Option 2
was dropped as extra workflow logic for little gain: pull requests are
merged quickly and tested on the nightly app afterwards; a single
pull request can still be installed from its CI artifact. Option 3 adds
a weekly promotion pull request, back-merges of fixes on `main`, two
protected branches and pull requests aimed at the wrong base, for the
same result as a tag.

# Consequences

- The [Flatpak workflow](../flatpak-workflow.md) has the inputs
  `release` (tags) and `nightly` (default branch); the rolling release
  `latest` is gone. An app with `nightly: true` needs the meson options
  `profile` and `build_label`.
- Both apps install side by side with separate settings and caches; the
  nightly app is named "<App> (Nightly)", has libadwaita's striped
  header bar and shows its source ("main · 8534d2c") in the About
  dialog.
- phosh-apps publishes the newest non-pre-release release (stable) and
  the pre-release `nightly`. An app without a tag `v<version>` fails
  the publish run, so the first tag must exist before phosh-apps
  switches.
- `main` still has to stay installable, but a broken `main` only
  breaks the nightly app.
