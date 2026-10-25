---
type: Decision Record
title: Pinned dependencies with automated updates
description: Dependencies are pinned exactly and kept current by bots that open pull requests, instead of floating on the newest version.
tags: [decision, dependencies, updates, licensing]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
---

# Status

Accepted (2026-10-25).

# Context

The owner wants every app on the newest versions of its dependencies and
wants their licences followed. Flatpak sources need checksums, so
"always latest" cannot float at build time without giving up
reproducible builds, and an unreviewed update can change a licence or
break the build on the phone.

# Decision

- Pin every dependency exactly: Flatpak sources by URL and checksum,
  the GNOME runtime by branch, GitHub Actions by major tag.
- Bots propose updates: flatpak-external-data-checker (weekly pull
  request), a runtime check (issue) and Dependabot (GitHub Actions).
  CI builds every proposal; a person merges it. See
  [dependency updates](../dependency-updates.md).
- Licences are part of the same gate: REUSE for own files, an inventory
  of bundled modules, licence texts in the bundle and published sources,
  all checked in CI. See [licensing](../licensing.md).

# Consequences

- Updates arrive as small pull requests every week; merging them is the
  only manual work.
- Pull requests opened with `GITHUB_TOKEN` do not start CI; each app
  needs an `UPDATE_TOKEN` secret for fully automatic checks.
- Adding a module means adding `x-checker-data`, a licence install and an
  inventory entry, or CI fails.
- Bundles grow by a source bundle per architecture in the shared
  repository.
