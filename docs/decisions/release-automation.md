---
type: Decision Record
title: Release automation with changelog fragments and a release pull request
description: User-facing notes come from per-pull-request fragments, a release pull request writes them into the metainfo, merging it tags the release; screenshots are taken by CI from the built Flatpak and published as release assets.
tags: [decision, release, changelog, screenshots, ci]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:00:00Z }
---

# Status

Accepted (2026-10-25): the owner asked to automate the changelog and the
screenshots following best practice; the options below were proposed
and implemented with the recommended choice.

# Context

The metainfo `<release>` was written by hand and the version bumped in
three files; GitHub Releases had generated notes from pull request
titles, so the two texts drifted. The metainfo listed no screenshots, so
GNOME Software showed none. The owner wants weekly stable releases and
merges every pull request in person.

# Decision

1. **Changelog fragments** (`changelog.d/<slug>.<type>.md`, the towncrier
   pattern) instead of Conventional Commits or a pull request body
   section. Commit messages are written for developers; the metainfo
   needs one sentence for users. A fragment is reviewed with the code,
   lives in the repository and causes no merge conflicts.
2. **A release pull request** (the release-please pattern) instead of
   releasing automatically: a weekly job proposes the release, the owner
   merges it, the merge creates the tag. Merging stays with the owner;
   the tag is never typed by hand.
3. **The metainfo is the only source** of release notes: GNOME Software,
   the About dialog and the GitHub Release all read it.
4. **Screenshots taken by CI from the built Flatpak**, with recorded
   data and declared shots (`release.toml`), published as **release
   assets** of the tag that the metainfo points to. Committing PNGs would
   grow the repository with every UI change; taking them from the
   Flatpak shows what ships and smoke-tests the app.
5. The logic lives in one toolkit script, `scripts/release.py`, called
   by the reusable workflows, so every app gets it by adding a
   `release.toml`.

# Consequences

- Pull requests that change the app need a fragment or the label
  `no-changelog`; the check *Changelog* is required in the app's ruleset.
- The release workflow needs a `RELEASE_TOKEN` (Contents and Pull
  requests write), because pull requests and tags made with
  `GITHUB_TOKEN` start no CI.
- States worth a screenshot need `app.*` actions and the app needs a
  recorded-data mode.
- Rejected: git-cliff/release-please from commit messages (developer
  wording), fully automatic weekly tags (no review of the text),
  screenshots in git (repository growth), screenshots from the host
  Python instead of the Flatpak (different libraries than shipped).
