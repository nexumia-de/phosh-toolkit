---
type: Concept
title: Owner checks
description: What only the owner can do after the issue clean-up of 2026-11-22 - settings, accounts, tags, device and CI observations - as one checklist; the closed issues point here.
tags: [owner, checklist, planning]
generated: { by: claude-code/2.1.330, at: 2026-11-22T12:00:00Z }
---

# Why

On 2026-11-22 every open issue of this repository was closed: done,
decided, or reduced to a step that needs the owner's account, a
repository setting, a device or a failure that only shows up in CI.
Those steps are collected here instead of staying open as issues
([planning](planning.md)). Tick an item off by deleting it.

# Checklist

## UI tests that hang in CI (issue 27)

Not reproduced outside GitHub's runners, so the cause is not known.

- [ ] When a UI test of Ephyra or Nauta times out in CI again (after the
  app pins the toolkit tag that has this change), open the failed run's
  log: `testing.run_until()` now prints the stack of every thread before
  its `TimeoutError`. Workers inside `Soup.Session.send` mean requests
  to the stopped test server fill the pool of
  `phosh_toolkit.tasks`; an idle pool means the answer was delivered to
  a window that is gone. Open a new issue with that stack.

## Own location on the phone (issue 22)

`phosh_toolkit.location` is tested against a stand-in portal only.

- [ ] After Cirro (nexumia-de/cirro#49) or Vestigia uses the shared
  module: on the phone, tap "Show my location", allow the portal's
  dialog and see the position appear; refuse once and see the app's
  message instead of a hang.

## Rulesets and the new checks (issue 18)

- [ ] phosh-toolkit: after the pull request is merged, import
  `.github/rulesets/main.json` again (Settings → Rules → Rulesets →
  delete "protect main" → Import a ruleset). It now requires
  `validate`, `lib` and `flatpak / Flatpak OK`. Until then the old
  ruleset keeps working, because the build jobs kept their names.
- [ ] Each app: its ruleset still lists `flatpak / REUSE compliance`
  and the two `flatpak / Build (…)` checks, which goes on working. When
  an app's pull request switches its `.github/rulesets/main.json` to
  `flatpak / Flatpak OK`, import that file again.
- [ ] Apps call the workflows at `@main` today, so the Precheck job
  runs in every app from the merge on. Its metadata checks pass on all
  seven apps (run locally on 2026-11-22); actionlint on the apps'
  workflow files could not be run in the cloud session. If an app's
  Precheck fails on "Lint workflow files", the annotation names the
  file and line.

