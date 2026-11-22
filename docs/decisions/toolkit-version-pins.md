---
type: Decision Record
title: Toolkit versions are plain tags; apps pin the reusable workflows to them
description: Apps call the toolkit's reusable workflows at the commit of a toolkit tag instead of @main; the workflows check out their own scripts at job.workflow_sha; a pull request that changes the Flatpak workflow also builds a real app.
tags: [decision, ci, dependencies, reusable-workflows]
generated: { by: claude-code/2.1.330, at: 2026-11-22T12:00:00Z }
sources:
  - id: issue-19
    resource: https://github.com/nexumia-de/phosh-toolkit/issues/19#issuecomment-6824571268
    title: Issue 19, the owner's decision of 2026-11-12
  - id: contexts
    resource: https://github.com/github/docs/blob/d7487f5debb5/content/actions/reference/workflows-and-actions/contexts.md
    title: GitHub Docs source, Contexts reference, job context (job.workflow_ref, job.workflow_sha, job.workflow_repository), read 2026-11-22
---

# Status

Accepted. The owner decided the three points on 2026-11-12[^issue-19];
the mechanism was worked out on 2026-11-22.

# Context

Apps called `…/flatpak.yml@main` and the jobs checked the toolkit's
scripts out at `toolkit-ref: main`. A broken commit on the toolkit's
`main` broke the CI and the releases of every app at once, also a tag
release that was already running, and it contradicted
[pinned dependencies](pinned-dependencies.md).

# Decision

1. **Plain tags** `v<major>.<minor>.<patch>` on `main`, made with the
   manual workflow *Tag release*. No changelog fragments or release pull
   request for the toolkit: its users are the apps' agents, who read
   `docs/log.md`.
2. **Apps pin** all reusable workflows to the commit of a tag,
   `@<sha> # v0.7.0`; Dependabot's `github-actions` updates propose the
   next tag.
3. **One pin only.** A job of a reusable workflow knows the commit of
   its own workflow file as `job.workflow_sha`[^contexts]; the toolkit
   checkouts use `inputs.toolkit-ref || job.workflow_sha`. Callers no
   longer pass `toolkit-ref`, so there is no second value that
   Dependabot would not update.
4. **A real app before the tag.** A pull request that changes
   `.github/workflows/flatpak.yml` or `scripts/` runs the self-test job
   `app`: the Flatpak workflow of that pull request builds Pulsus (two
   modules, release screenshots) through the input `app-repository`.
   Other pull requests skip it.

# Alternatives

- **Releases like the apps** (fragments, release pull request): rejected
  by the owner as too much for a repository without end users.
- **Keep `toolkit-ref` and ask callers to keep it equal**: two values
  per call that must match, and Dependabot only updates `uses:`.
- **Run an app's CI by `repository_dispatch`**: needs a token with
  access to the app repository and reports nothing on the toolkit's
  pull request. Building the app from the toolkit's own run needs no
  secret, because the apps are public.
- **Cirro as the real app**: its build (numpy, HDF5, h5py from source)
  takes much longer than Pulsus' and tests the same workflow paths.

# Consequences

- The `app` job covers the Flatpak workflow on pull requests only; the
  release, nightly and update-check paths run first in an app that moves
  to the new tag, where the pin limits a failure to that pull request.
- Until an app's own pull request switches it, it stays on `@main`.
- `job.workflow_sha` is not available on GitHub Enterprise Server; the
  repositories are on github.com.

[^issue-19]: Issue 19, the owner's decision of 2026-11-12
[^contexts]: GitHub Docs source, Contexts reference
