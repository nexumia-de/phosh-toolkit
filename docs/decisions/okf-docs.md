---
type: Decision Record
title: OKF for documentation
description: Project knowledge is stored as an Open Knowledge Format v0.2 bundle in docs/ and updated with the code.
tags: [decision, documentation, okf]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
sources:
  - id: okf-spec
    resource: https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md
    title: Open Knowledge Format specification v0.2
---

# Status

Accepted (2026-10-24).

# Context

Most changes are made by coding agents. Knowledge that only exists in a
chat is lost after the session. The knowledge must be readable by humans
and agents without special tooling and must be reviewable in diffs.

# Decision

Each repository keeps its knowledge in `docs/` as an OKF v0.2
bundle:[^okf-spec]

- one markdown file per concept with YAML frontmatter; `type` is
  required, `title`, `description`, `tags` are always set, and
  `resource` when the concept describes a concrete file or URL;
- `generated: { by, at }` records who last wrote the content, using the
  actor convention (`<tool>/<version>` for agents, `human:<id>` for
  people); `verified` is added only by whoever actually checked it;
- external facts are listed in `sources` and cited with footnotes keyed
  by the source `id`;
- `status` (`draft`, `stable`, `deprecated`) and `stale_after` mark
  lifecycle;
- `docs/index.md` is the entry point (with `okf_version: "0.2"`),
  `log.md` records changes newest first;
- cross-references are plain relative markdown links, so they also work on
  GitHub.

Knowledge is updated in the same commit as the code change it describes.

# Consequences

- Agents can load the bundle progressively starting at `docs/index.md`.
- Trust and freshness are visible in frontmatter.
- Every code change needs a check whether a concept or `log.md` must be
  updated.

[^okf-spec]: Open Knowledge Format specification v0.2
