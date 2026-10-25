---
type: Decision Record
title: Own Flatpak repository for all apps
description: All apps are published as one signed Flatpak repository on GitHub Pages instead of Flathub or single bundles.
tags: [decision, flatpak, distribution, repository]
generated: { by: claude-code/2.1.310, at: 2026-10-24T22:30:00Z }
---

# Status

Accepted (2026-10-24) by the owner.

# Context

Apps should be installable and updatable from GNOME Software on the
phone. Options:

1. **Flathub**: official, already configured on phones, but needs a
   review per app, accepts only working apps, wants domain/ownership
   verification and may require building Python dependencies from
   source.
2. **Single `.flatpak` bundles**: work today, but no updates.
3. **Own repository** on GitHub Pages: no review, updates through
   Software, one remote for all apps; needs a signing key and a publish
   job.

# Decision

Option 3, as one repository `suitably/phosh-apps` collecting the releases of
every app repository (originally the rolling release `latest`, now the
[release channels](release-channels.md))
([shared app repository](../app-repository.md)). Apps stay in their own
repositories ([one repository per app](one-repo-per-app.md)).

# Consequences

- One GPG key for all apps; losing it means every phone must re-add the
  remote, so it must be backed up.
- Every push to an app's `main` becomes an update on the phone (since
  2026-10-25 of the nightly app only, see
  [release channels](release-channels.md)); `main` has to stay
  installable.
- Flathub stays possible later for apps that become stable.
- GitHub Pages limits (1 GB site, soft 100 GB/month traffic) are far
  above the expected size.
