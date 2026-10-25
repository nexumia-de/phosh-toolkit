---
type: Playbook
title: Releases, changelog and screenshots
description: How app repositories release - changelog fragments per pull request, a release pull request that writes the metainfo <release>, an automatic tag, release notes from the metainfo and screenshots taken by CI from the built Flatpak.
resource: ../scripts/release.py
tags: [release, changelog, screenshots, metainfo, ci, flatpak]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:00:00Z }
sources:
  - id: appstream-releases
    resource: https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-releases
    title: AppStream specification, releases
  - id: appstream-screenshots
    resource: https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-screenshots
    title: AppStream specification, screenshots
  - id: gh-token
    resource: https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication#using-the-github_token-in-a-workflow
    title: GitHub Docs, events triggered by GITHUB_TOKEN do not create new workflow runs
---

# One source for "what's new"

The `<release>` elements of the app's metainfo are the changelog. GNOME
Software shows them as "What's New", the app's About dialog shows the
newest one (`AdwAboutDialog` release notes), and the GitHub Release of a
tag gets the same text. Nobody writes them by hand: they are collected
from changelog fragments.[^appstream-releases] Why this design:
[decision](decisions/release-automation.md).

```
pull request ── adds changelog.d/<slug>.<type>.md ── check "Changelog"
      │ merged
main ─┴─ weekly (or by hand): "Release pull request"
           release.py prepare: version bump, <release>, <screenshots>,
           fragments deleted ─► PR "Release 0.2.0" (CI, screenshot artifact)
      │ merged by the owner
main ─┴─ "Tag release": newest <release> changed ─► tag v0.2.0
           Flatpak workflow: build, screenshots, GitHub Release with the
           metainfo notes, bundles and screenshots ─► phosh-apps
```

# Pieces

- `scripts/release.py` (standard library only) does all file changes;
  the reusable workflows only call it. Tests: `tests/test_release.py`.
- `release.toml` in the app repository root configures it (example:
  [`examples/release.toml`](../examples/release.toml), Cirro's
  `release.toml`):
  - `metainfo`: the stable metainfo file in the source tree.
  - `version-files`: files that contain the version exactly once in
    quotes (`version: '0.1.0'` in `meson.build`, `VERSION = "0.1.0"`).
  - `fragments`: directory of the fragments, default `changelog.d`.
  - `[screenshots]` and `[[screenshots.shot]]`: see below.
- Reusable [`release.yml`](../.github/workflows/release.yml): jobs
  *Changelog*, *Release pull request*, *Tag release*.
- Reusable [`flatpak.yml`](../.github/workflows/flatpak.yml): screenshots,
  release notes, development release for the nightly app.

# Changelog fragments

Every pull request that changes something users notice adds
`changelog.d/<slug>.<type>.md`: one sentence for users, in English;
blank lines separate several entries. Types and their version bump
(pre-1.0 and after, MAJOR is only raised by hand with `--version`):

| Type | Meaning | Bump |
|---|---|---|
| `feature` | something new | minor |
| `improvement` | something works better | patch |
| `fix` | something broken works again | patch |

The check *Changelog* fails a pull request that changes anything except
`docs/`, `tests/`, `.github/`, Markdown files, `LICENSES/`, `REUSE.toml`,
`.gitignore` and `release.toml` without adding a fragment. Internal
changes get the label `no-changelog` instead. Branches `release/*`,
`dependabot/*` and `update-*` (flatpak-external-data-checker) are
exempt. Locally: `python3 ../phosh-toolkit/scripts/release.py check`.

# Release pull request

The job *Release pull request* runs on the app's schedule (Cirro:
Mondays) and by hand (*Actions → Release → Run workflow*, optionally
with a version). Without fragments the scheduled run does nothing.
`release.py prepare`:

1. computes the version from the newest stable `<release>` and the
   fragment types (or takes `--version`; it must be newer),
2. replaces the old version in every `version-files` entry,
3. adds `<release version date>` with a `<ul>` of the fragments
   (features first) to the metainfo,
4. rewrites `<screenshots>` with the URLs the tag release will have
   (`https://github.com/<repo>/releases/download/v<version>/<file>`),
5. deletes the fragments.

The job commits that to `release/v<version>`, force-pushes it and opens
or updates the pull request "Release <version>", whose body shows the
notes. The owner reviews the text and the screenshot artifact of its
Flatpak run and merges.

# Tag and GitHub Release

On every push to the default branch, *Tag release* compares the newest
stable `<release>` with the one in the parent commit. If it changed and
`v<version>` does not exist yet, it creates the tag through the API.
The Flatpak workflow's tag run checks the tag against the metainfo,
takes the screenshots, fails if the metainfo lists a screenshot that was
not taken, and creates the GitHub Release with the `release.py notes`
text, the bundles and all screenshots (light and dark) as assets.
Pre-release tags (`v1.0.0-rc.1`, made by hand) get GitHub's generated
notes.

Tags and pull requests made with the default `GITHUB_TOKEN` start no
workflows.[^gh-token] The release workflow therefore needs the secret
`RELEASE_TOKEN`, a fine-grained token with **Contents** and **Pull
requests** read/write on the app repository; without it the jobs fail
with a message (a tag can always be pushed by hand).

# Nightly app

The nightly build runs `release.py devel` before building: the metainfo
gets a `<release type="development">` with the version
`<next>~dev.<date>.<commit>` and the pending fragments. GNOME Software
and the About dialog of the nightly app show what is new on `main`; the
stable comparison (`release.py latest`) skips development releases.

# Screenshots

`release.toml` declares *what* to show; CI takes every shot at two
sizes and in two colour schemes from the **built Flatpak**, so the
pictures show exactly what ships, and the run doubles as a smoke test
(the app must start in its runtime and show its window):

| Size | Viewport | Scale | File |
|---|---|---|---|
| phone | 360×720 (Phosh) | 2 | `<name>-phone-light.png`, `-dark.png` |
| desktop | 1000×700 | 1 | `<name>-desktop-light.png`, `-dark.png` |

```toml
[screenshots]
env = { MYAPP_DEMO = "{root}/tests/data/demo" }  # {root}: the app repository
expose = ["{root}/tests/data/demo"]               # read-only in the sandbox
delay = 3                                         # seconds before the shot

[[screenshots.shot]]
name = "forecast"                  # file name part: lower case, digits, '-'
caption = "Rain forecast one hour ahead"
actions = ["app.step-time(12)"]    # activated after the window appeared
```

- **Adding a shot** (agents: whenever a feature is worth showing): add a
  `[[screenshots.shot]]` with a caption and the actions that open the
  state, then check it locally. `actions` are application actions
  activated over D-Bus like `gapplication action` does; parameters are
  GVariant text in brackets. GTK exports only `app.*` actions on D-Bus,
  not `win.*`, so an app gives the states it wants to show (a page, a
  dialog, a time) `app.*` actions that forward to the active window.
  Those actions should be real features (keyboard shortcuts, menu
  entries), not screenshot-only code.
- **Deterministic data**: shots must not depend on live data or the
  time. The app reads recorded data from a directory named by an
  environment variable (Cirro: `CIRRO_DEMO_DATA`), exposed with `expose`.
  Map tiles and similar static assets may come from the network.
- **Metainfo**: the release pull request lists the phone and desktop
  light shots of every entry (the first is `type="default"`); the dark
  ones are only release assets, because a store that ignores the
  `environment` attribute would show each screenshot
  twice.[^appstream-screenshots]
- **Pull requests**: the x86_64 build uploads the artifact
  `<bundle>-screenshots`, so UI changes can be reviewed without
  installing anything.

Locally, after building and installing the Flatpak (`flatpak-builder
--user --install …`):

```sh
python3 ../phosh-toolkit/scripts/release.py screenshots --out shots -- flatpak run de.nexumia.MyApp
```

It calls [`screenshot.sh`](screenshot-testing.md) once per file.

# Verified (2026-10-25)

- Locally (Ubuntu 24.04, flatpak 1.14.6, GNOME 51 runtime): Cirro and
  the demo app, installed as Flatpaks, render under Broadway with
  `--filesystem=xdg-run/broadway<N+1>.socket`; `app.about` and
  `app.step-time(12)` activate over D-Bus; `ADW_DEBUG_COLOR_SCHEME=prefer-dark`
  switches the style; `release.py prepare` output passes
  `appstreamcli validate`; the release and tag job scripts produce the
  expected commit and tag call on a copy of Cirro.
- GTK 4 (GNOME 51) exports only the application object
  (`/de/nexumia/Cirro`, `org.gtk.Actions`) on the session bus, no
  `/window/<id>` objects.

[^appstream-releases]: AppStream specification, releases
[^appstream-screenshots]: AppStream specification, screenshots
[^gh-token]: GitHub Docs, automatic token authentication
