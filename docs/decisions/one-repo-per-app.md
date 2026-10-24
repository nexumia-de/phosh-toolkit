---
type: Decision Record
title: One repository per app
description: Every app, including forks of third-party apps, lives in its own repository.
tags: [decision, repository, organization]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
---

# Status

Accepted (2026-10-24).

# Context

Apps have independent release cycles, issue trackers and, for forks,
their own upstream. A monorepo would mix histories and make upstream
merges of forked apps hard.

# Decision

Each app lives in its own GitHub repository under `suitably`. Forks of
third-party apps keep `main` identical to upstream and carry all Phosh
changes on a branch named `phosh`. Shared material lives in the
[central toolkit](central-toolkit.md).

# Consequences

- Clean per-app history, issues, releases and CI.
- Upstream merges into forks stay simple: update `main`, merge into
  `phosh`.
- Shared rules must be consumed from the toolkit instead of copied (see
  [toolkit usage](../toolkit-usage.md)).
