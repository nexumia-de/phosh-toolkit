---
type: Workflow
title: Planning with issues and milestones
description: Work items are GitHub issues, milestones group them into releases of the plan, labels classify them; the app's roadmap.md keeps only the goals; an optional GitHub Project shows all repositories on one board.
tags: [planning, roadmap, issues, milestones, labels, github]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:46:00Z }
sources:
  - id: gh-milestones
    title: About milestones
    url: https://docs.github.com/en/issues/using-labels-and-milestones-to-track-work/about-milestones
  - id: gh-projects
    title: About Projects
    url: https://docs.github.com/en/issues/planning-and-tracking-with-projects/learning-about-projects/about-projects
  - id: gh-closing
    title: Linking a pull request to an issue
    url: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue
---

# Why

A checklist in a markdown file cannot be discussed, assigned, linked to
the pull request that does the work, or closed by it; it is edited by
hand and drifts from the truth. GitHub issues, milestones, labels and
Projects do all of that and cost nothing for public and private
repositories[^gh-milestones][^gh-projects]. Decision:
[planning in GitHub issues](decisions/planning-issues.md).

# Where things live

| What | Where |
|---|---|
| A piece of work (feature, bug, task, measurement, open decision) | One **issue** in the app's repository |
| A step of the plan (M2, M3, …) | A **milestone** in the app's repository; progress bar and list of its issues come for free |
| What a milestone is for, its exit criteria, priorities, risks | The app's `docs/roadmap.md` (goals only, no task checklists) |
| Ideas not scheduled yet | Open issues **without a milestone** (the backlog) |
| A decision that was made | `docs/decisions/` as before; the issue that asked for it links to it and is closed |
| What changed | `docs/log.md` and the changelog fragments as before |
| Everything across repositories at a glance | Optional organisation **Project** (see below) |

The roadmap links each milestone's page
(`https://github.com/<owner>/<repo>/milestone/<n>`) instead of listing
its tasks, so there is one list and it is always current.

# Milestones

- Title `M<n> – <goal>`, e.g. `M3 – Point nowcast and places`; the
  description repeats the goal in one sentence.
- Work on the lowest open milestone first. Agents do not start issues of
  a later milestone without asking the owner.
- A milestone is closed when all its issues are closed; the roadmap
  section then says "done" and keeps its goal text as history.
- No due dates unless the owner sets them.

# Labels

Keep the GitHub defaults (`bug`, `enhancement`, `documentation`,
`question`, `duplicate`, `invalid`, `wontfix`, `good first issue`,
`help wanted`) and add:

| Label | Use |
|---|---|
| `area: <part>` | The part of the app, e.g. `area: radar`; one colour for all area labels; each app defines its own set |
| `needs decision` | Blocked on the owner; the result becomes a decision record |
| `on device` | Needs a test or measurement on the phone; agents in the cloud cannot finish it alone |
| `no-changelog` | Pull requests without a user-visible change ([releases](releases.md)) |

Priority is the milestone and the order in the roadmap, not a label.

# Issues and pull requests

- Bigger issues carry a task list (`- [ ]`) in their body; GitHub shows
  the progress in lists and on the board.
- An issue that depends on another names it (`Depends on #20`).
- A pull request that finishes an issue says `Closes #<n>` in its body,
  so merging closes the issue and links both[^gh-closing]. A pull
  request that only advances it says `Part of #<n>`.
- Findings that mean future work (a missing measurement, a follow-up, a
  bug seen on the way) become a new issue, not a line in a document or
  a chat message. Facts and decisions still go into `docs/`.
- Agents with API access create and label issues and set milestones
  themselves; otherwise they list the proposed issues for the owner.

# Organisation Project (optional, set up by the owner)

A Project shows the issues of all repositories on one board, table or
roadmap. It cannot be created by agents: Projects need the GraphQL API,
which cloud sessions cannot reach. Setup, once:

1. Organisation → **Projects** → **New project** → template *Roadmap*
   (or *Board*), name it "Phosh apps".
2. **Settings → Workflows**: enable *Auto-add to project* for each
   repository with the filter `is:issue,pr is:open`, and *Item closed* →
   status *Done*.
3. Add views: a *Board* grouped by status, a *Table* grouped by
   **Milestone**, a *Roadmap* by milestone.

The Project only displays issues; milestones and labels in the
repositories stay the source of truth, so nothing breaks without it.
