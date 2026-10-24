# Agent rules for Phosh apps

These rules apply to this repository (phosh-toolkit) and to every app
repository that imports this file with `@../phosh-toolkit/AGENTS.md`.
Agents that do not support imports: read this file from the sibling
checkout `../phosh-toolkit/AGENTS.md` before working on an app.

## Language

- Everything in this repository and in all app repositories is English:
  code, comments, docs, commit messages, PR texts, issue texts.
- The user may write in German or English. Always reply in English.

## Target platform

- Phosh on a phone: **360×720 logical px**, touch input, **aarch64**.
  Details: [docs/device.md](docs/device.md), [docs/phosh.md](docs/phosh.md).
- Every app must also work as a normal desktop window.

## UI

- Adaptive GTK4 + libadwaita UI: use `AdwBreakpoint` for layout changes
  and `AdwNavigationSplitView` for sidebar/content layouts.
- No horizontal scrolling at 360 px width. Minimum window size 360×294.
- Touch first: no hover-only affordances, large targets, forms scroll
  vertically for the on-screen keyboard.
- Full guideline: [docs/adaptive-libadwaita.md](docs/adaptive-libadwaita.md).
- Check every UI change with `scripts/screenshot.sh` at 360×720 (and once
  at a desktop size) and look at the result before committing. See
  [docs/screenshot-testing.md](docs/screenshot-testing.md).

## Metadata

- `.desktop` file: `X-Purism-FormFactor=Workstation;Mobile;`
- metainfo:

  ```xml
  <recommends>
    <display_length compare="ge">360</display_length>
  </recommends>
  <supports>
    <control>touch</control>
  </supports>
  ```

- Run before every commit that touches them, and fix all errors and
  warnings:

  ```sh
  appstreamcli validate path/to/*.metainfo.xml
  desktop-file-validate path/to/*.desktop
  ```

## Distribution and CI

- Apps ship as Flatpak (GNOME runtime from Flathub), built for x86_64 and
  aarch64 with the reusable workflow
  `suitably/phosh-toolkit/.github/workflows/flatpak.yml`. See
  [docs/flatpak-workflow.md](docs/flatpak-workflow.md).
- Host setup: `setup.sh` (Ubuntu 24.04, idempotent).

## Repositories and branches

- One repository per app; shared material lives in phosh-toolkit.
- Forks of third-party apps: work only on a branch named `phosh`. Keep
  `main` identical to upstream so upstream merges stay clean. Never commit
  Phosh changes to `main` of a fork.

## Knowledge

- Knowledge lives in the OKF v0.2 bundle in `docs/` (entry point
  `docs/index.md`). Read it before starting work.
- Update the bundle **in the same commit** as the code change it
  describes: edit or add the concept file, update `docs/index.md` when
  concepts are added or removed, and add an entry to `docs/log.md`.
- Never leave knowledge only in chat. Findings, decisions, workarounds and
  device facts go into `docs/`.
- One file per concept with YAML frontmatter: `type` (required), `title`,
  `description`, `tags`, `resource` where applicable, `generated: { by,
  at }`, external facts in `sources` cited with `[^id]` footnotes. Agents
  use `<tool>/<version>` as actor; never write a `human:` actor in
  `verified` unless that person actually confirmed the content.
- New decisions go into `docs/decisions/` as `type: Decision Record`.
- Cross-references are plain relative markdown links.

## Before committing

1. Build and run the tests of the touched project.
2. `appstreamcli validate` and `desktop-file-validate` if metadata changed.
3. `scripts/screenshot.sh` at 360×720 if the UI changed.
4. `docs/` updated in the same commit.
5. Commit message and all texts in English.
