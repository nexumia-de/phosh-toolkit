---
type: Decision Record
title: AGENTS.md for vendor neutrality
description: Agent rules live in AGENTS.md so any coding agent can use them; CLAUDE.md only imports AGENTS.md.
tags: [decision, agents, vendor-neutral]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
---

# Status

Accepted (2026-10-24).

# Context

Different coding agents read different instruction files. Keeping the
rules in a vendor-specific file would lock the repositories to one agent
or require duplicated, drifting copies.

# Decision

- All rules live in `AGENTS.md`, a plain markdown file that most agents
  read.
- `CLAUDE.md` contains only `@AGENTS.md`, which Claude Code resolves as
  an import.
- App repositories start their `AGENTS.md` with
  `@../phosh-toolkit/AGENTS.md` (see [toolkit usage](../toolkit-usage.md)).
- `setup.sh` and the scripts make no assumptions about a particular
  agent or cloud environment.

# Consequences

- Switching or mixing agents needs no changes to the rules.
- Agents without import support must follow the referenced path
  themselves; the prose in each `AGENTS.md` says so.
