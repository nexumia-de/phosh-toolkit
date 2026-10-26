---
type: Decision Record
title: Planning in GitHub issues and milestones
description: Work items are GitHub issues grouped by milestones and labels; roadmap.md keeps only goals; an organisation Project is an optional view on top.
tags: [decision, planning, roadmap, issues, milestones]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:46:00Z }
---

# Status

Accepted (2026-10-25): the owner asked for the free best practice
instead of tracking the plan in `docs/roadmap.md`, and to implement it.

# Context

Cirro's plan lived as checkboxes in `docs/roadmap.md`, while the owner
had started filing feature requests as GitHub issues. The two lists did
not know about each other: new issues had no milestone, roadmap items
had no place for discussion, and nothing closed a checkbox when a pull
request merged. The solution must be free, work for several app
repositories, and be usable by agents.

# Options

1. **Markdown checklists** (status quo): versioned, but no discussion,
   no links from pull requests, edited by hand, and a second list next
   to the issues.
2. **GitHub issues + milestones + labels**, optional **GitHub Project**
   across repositories: free, built into the code host, issues close
   from pull requests, milestones give progress bars, the REST API lets
   agents file and sort issues.
3. **External tools** (Linear, Jira, Trello, Taiga free tiers): richer
   planning, but a second account and place, not open to contributors
   by default, and links to code by integration only.
4. **Roadmap as code** (milestones and labels declared in YAML and
   synced by a workflow): reproducible, but needs a token and a
   workflow for what the web UI does in seconds, for a handful of
   milestones.

# Decision

Option 2. Issues are the work items, milestones the steps of the plan,
labels classify. The app's `docs/roadmap.md` keeps the principle, each
milestone's goal and exit criteria and the risks, and links the
milestone pages. An organisation Project is recommended as a view but
not required. Details: [planning with issues and milestones](../planning.md).

# Consequences

- `AGENTS.md` tells agents to work from the issues of the current
  milestone, to reference issues in pull requests, and to file future
  work as issues.
- Project boards cannot be created or edited by agents in cloud
  sessions (no GraphQL); the owner sets the Project up once.
- The plan's history is in the closed issues and milestones; the
  roadmap keeps a one-line summary per finished milestone.
