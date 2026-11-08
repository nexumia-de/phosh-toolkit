---
type: Decision Record
title: Lean agent rules
description: Shared agent rules are split into a core file for every repository and a file for GTK apps, kept short, with a token budget section.
tags: [decision, agents, tokens]
generated: { by: claude-code/2.1, at: 2026-11-08T12:00:00Z }
sources:
  - id: gloaguen2026
    title: "Evaluating AGENTS.md: Are Repository-Level Context Files Helpful for Coding Agents? (arXiv:2602.11988, ICLR 2026)"
    url: https://arxiv.org/abs/2602.11988
  - id: fable-plan
    title: Claude Fable models on your plan (Anthropic Help Center)
    url: https://support.claude.com/en/articles/15424964-claude-fable-models-on-your-plan
---

# Status

Accepted (2026-11-08, at the owner's request).

# Context

The owner's Max plan reached 88% of its weekly limit while the agents
worked across the repositories. Every repository imported the whole
`AGENTS.md` of phosh-toolkit (about 2,200 words), although ATL, aports,
phosh-apps and QuestArc had to list which half of it did not apply. With
the repository's own rules that was about 5,000 tokens on every request
of every session.

A study of AGENTS.md-style context files across several coding agents,
Claude Code among them, found that context files raised inference cost
by over 20% and made agents search, read and test more, while task
success did not improve (generated files) or improved only slightly
(human-written files). Agents follow the instructions they are given;
repository overviews did not help, rules about non-standard practices
did. The authors recommend minimal files.[^gloaguen2026] Fable models
draw from the same weekly limit as other models and use it faster, so
saved tokens count for every model.[^fable-plan]

# Decision

- `agents/core.md` holds the rules for every repository; GTK apps also
  import `agents/gtk-app.md`. Repositories import only what applies, so
  "which rules do not apply" sections are gone.
- A rule stays in these files only if agents get it wrong without it.
  Explanations, examples and background live in `docs/` and are linked,
  read when the task touches them.
- `agents/core.md` has a "Token budget" section: one task per session,
  targeted reads, short command output, narrowest check first, subagents
  only for real parallel work, no polling, no needless screenshots.
- CI is watched by subscribing to pull request activity, not by polling.
- `phosh-toolkit/AGENTS.md` keeps working as a single import of both
  files plus the toolkit's own rules.

# Consequences

- Repositories that are not GTK apps load about 900 instead of 2,200
  shared words; GTK apps load about 1,700, including the new token
  budget section.
- Adding a shared rule means choosing core or GTK app.
- The study measured single-issue Python tasks; long multi-repository
  work was not measured, so the savings here are an estimate.
