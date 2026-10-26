---
type: Playbook
title: Flathub readiness
description: What is prepared so that an app can be submitted to Flathub later (generated submission manifest, linter checks), what still blocks a submission, and the submission steps. Apps ship from the own repository until then.
tags: [flathub, flatpak, release, linter, verification]
generated: { by: claude-code/2.1.310, at: 2026-10-25T21:00:00Z }
sources:
  - id: requirements
    resource: https://docs.flathub.org/docs/for-app-authors/requirements
    title: Flathub requirements (checked 2026-10-25)
  - id: submission
    resource: https://docs.flathub.org/docs/for-app-authors/submission
    title: Flathub submission (checked 2026-10-25)
  - id: verification
    resource: https://docs.flathub.org/docs/for-app-authors/verification
    title: Flathub verification (checked 2026-10-25)
---

# Status

The owner decided on 2026-10-25 to **prepare** Flathub submissions but
publish only through the own repository
(`https://flatpak.nexumia.de/`, see [shared app repository](app-repository.md))
for now. The nightly apps (`<app id>.Devel`) stay there in any case.

# What is prepared

- **Submission manifest.** Flathub builds an app from a public source,
  not from a checkout. Every tag release therefore carries
  `<app id>.json` as a release asset: the app's manifest
  (`flatpak-builder --show-manifest`) with the app module's
  `type: dir` source replaced by `type: git` with the tag and its
  commit, plus `x-checker-data` (`tag-pattern ^v([\d.]+)$`) so Flathub's
  update bot proposes the next tag. Made by
  `scripts/release.py flathub-manifest`; verified on 2026-10-25 by
  building Cirro from `v0.1.0` with it.
- **Linter.** The job *Flathub linter* ([Flatpak workflow](flatpak-workflow.md#flathub-linter))
  checks the app manifest and the generated submission manifest on every
  run.

# What still blocks a submission

| Blocker | Rule | What to do |
|---|---|---|
| Prebuilt binaries in the manifest (compiled wheels, binary tarballs) | "All source available submissions must be built entirely from source code", including runtime dependencies in the manifest[^requirements] | Build from source archives. Cirro does since 2026-10-25: numpy, HDF5 and h5py from source, only pure-Python build tools as wheels, removed after the build ([its dependencies](../../cirro/docs/dependencies.md)). |
| `https://nexumia.de` answers 404 | Linter `appid-url-not-reachable`: the domain from the app id must be reachable[^requirements] | Serve a page or a redirect there; then remove the exception in the workflow. |
| No screenshots in the metainfo | Linter `metainfo-missing-screenshots` | Done by an app's first release pull request ([releases](releases.md)). |
| Domain verification (for the "verified" badge) | Token at `https://nexumia.de/.well-known/org.flathub.VerifiedApps.txt`, one line per app; the token is shown on Flathub after the submission[^verification] | Serve it as a real file, not a redirect (whether redirects are followed is not documented): a Cloudflare Worker route for `nexumia.de/.well-known/*` or a small Pages site with `nexumia.de` as custom domain. |

Not blockers: the linter's `appstream-screenshots-not-mirrored-in-ostree`
on a locally built repository (Flathub's build service mirrors
screenshots itself), `--share=network` (needed for the data; declared
in the manifest with a comment), the licences (redistributable and
declared in the metainfo).

# Submitting (when the owner decides to)

1. Make sure the blockers above are gone and the newest tag release has
   its `<app id>.json` asset.
2. Fork `flathub/flathub` with all branches and clone its `new-pr`
   branch (`gh repo fork --clone flathub/flathub && cd flathub && git checkout --track origin/new-pr`).[^submission]
3. Add the downloaded `<app id>.json` at the top level (plus
   `flathub.json` only to limit architectures; both are built), commit
   on a new branch and open a pull request against `new-pr`.
4. After review Flathub creates `flathub/<app id>`; later releases are
   pull requests there, proposed by Flathub's update bot from the tag
   pattern.
5. Verify the domain on flathub.org with the token, then decide whether
   the own repository keeps the stable app (both remotes would then
   offer the same app id; GNOME Software shows the source).

[^requirements]: Flathub requirements
[^submission]: Flathub submission
[^verification]: Flathub verification
