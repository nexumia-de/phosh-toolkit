---
type: Playbook
title: Branch protection
description: How main is protected in every repository with a GitHub ruleset imported from .github/rulesets/main.json.
tags: [github, rulesets, ci, branches]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:10:00Z }
sources:
  - id: rulesets
    resource: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository
    title: GitHub Docs, managing rulesets for a repository
  - id: rules
    resource: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets
    title: GitHub Docs, available rules for rulesets
---

# Goal

`main` changes only through pull requests whose CI is green. Agents
open those pull requests after each task (see `AGENTS.md`, "After the
task").

# The ruleset file

Every repository carries `.github/rulesets/main.json`, a ruleset in
GitHub's import format.[^rulesets] It targets the default branch and
contains:

* **Restrict deletions** and **block force pushes**.
* **Require a pull request**, with **0 required approvals**: GitHub does
  not let the owner approve their own pull requests, and pull requests
  opened by agents run under the owner's account. With 1 approval
  required nothing could ever be merged.
* **Require status checks**, strict (branch up to date), each check
  bound to GitHub Actions (`integration_id` 15368). The names are the
  check names as GitHub shows them on a pull request: a job called
  through a reusable workflow is `<caller job> / <job name>`, e.g.
  `flatpak / Build (x86_64)`.[^rules]
* **Bypass**: repository admins (`RepositoryRole` 5), for emergencies.

| Repository | Required checks |
|---|---|
| phosh-toolkit | `validate`, `flatpak / REUSE compliance`, `flatpak / Build (x86_64)`, `flatpak / Build (aarch64)` |
| cirro | `test`, `flatpak / REUSE compliance`, `flatpak / Build (x86_64)`, `flatpak / Build (aarch64)` |
| phosh-apps | none: its only workflow runs on pushes and a schedule, never on pull requests, so a required check would never report and block every merge |

`flatpak / Release bundles` is skipped on pull requests and must not be
required.

# Applying it

Agents in the cloud environment have no GitHub API access to repository
settings, so the owner imports the file once per repository:

1. Settings → Rules → Rulesets → **New ruleset → Import a ruleset**,
   choose `.github/rulesets/main.json` (download it from the repository
   first).
2. Delete any older hand-made ruleset for `main`; rules of several
   rulesets add up, so an old one does no harm but is confusing.

Adding checks by hand in the ruleset editor is error-prone: "Add checks"
only suggests checks that ran recently, and a name typed without the
`flatpak / ` prefix never matches, so the merge button stays blocked.

# Keeping it in sync

Renaming a CI job or the calling job (`flatpak:`) changes the check
name. Update `.github/rulesets/main.json` in the same pull request and
re-import it, otherwise every later pull request waits for a check that
no longer exists. A new app repository copies the cirro file and adjusts
its own test job name.
