---
type: Decision Record
title: Central toolkit
description: Host setup, agent rules, scripts, CI workflows and shared knowledge live in the phosh-toolkit repository.
tags: [decision, toolkit, reuse]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
---

# Status

Accepted (2026-10-24).

# Context

With [one repository per app](one-repo-per-app.md), copying setup scripts,
rules and CI into each repository would let them drift apart.

# Decision

`suitably/phosh-toolkit` is the single source for:

- `setup.sh` (host setup),
- `AGENTS.md` (shared agent rules),
- `scripts/screenshot.sh` (phone-size screenshots),
- `.github/workflows/flatpak.yml` (reusable Flatpak CI),
- `docs/` (shared knowledge bundle),
- shared app runtime code, once a second app needs it (see
  [code reuse](code-reuse.md)).

App repositories check it out side by side at `../phosh-toolkit` and
reference it (see [toolkit usage](../toolkit-usage.md)).

# Consequences

- A fix in the toolkit reaches every app at once.
- Breaking changes to the workflow inputs or scripts affect all apps; keep
  them backward compatible or update the apps in the same change set.
- App repositories depend on the sibling checkout being present.
