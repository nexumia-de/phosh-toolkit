# Agent rules for Phosh apps

These rules apply to this repository (phosh-toolkit) and to every app
repository that imports this file with `@../phosh-toolkit/AGENTS.md`.
Agents that do not support imports: read this file from the sibling
checkout `../phosh-toolkit/AGENTS.md` before working on an app.

> **Paths:** every path in this file (`docs/…`, `scripts/…`, `setup.sh`)
> is relative to the **phosh-toolkit checkout**. From an app repository
> they are `../phosh-toolkit/docs/…`, `../phosh-toolkit/scripts/…` and
> `../phosh-toolkit/setup.sh`. Commands below are written in that
> app-repository form; inside phosh-toolkit itself drop the
> `../phosh-toolkit/` prefix. Exceptions are marked: "the app's `docs/`"
> means the `docs/` of the repository you are working in.

## Language

- Everything in this repository and in all app repositories is English:
  code, comments, docs, commit messages, PR texts, issue texts.
- The user may write in German or English. Always reply in English.

## Target platform

- Phosh on a phone: **360×720 logical px**, touch input, **aarch64**.
  Details: [../phosh-toolkit/docs/device.md](docs/device.md), [../phosh-toolkit/docs/phosh.md](docs/phosh.md).
- Every app must also work as a normal desktop window.

## UI

- Adaptive GTK4 + libadwaita UI: use `AdwBreakpoint` for layout changes
  and `AdwNavigationSplitView` for sidebar/content layouts.
- No horizontal scrolling at 360 px width. Minimum window size 360×294.
- Touch first: no hover-only affordances, large targets, forms scroll
  vertically for the on-screen keyboard.
- Full guideline: [../phosh-toolkit/docs/adaptive-libadwaita.md](docs/adaptive-libadwaita.md).
- Check every UI change at 360×720 (and once at a desktop size) and look
  at the result before committing:

  ```sh
  ../phosh-toolkit/scripts/screenshot.sh -o shot.png -- <command that starts the app>
  ../phosh-toolkit/scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- <command>
  ```

  See
  [../phosh-toolkit/docs/screenshot-testing.md](docs/screenshot-testing.md).

## Metadata

- App id: `de.nexumia.<AppName>` (the owner's domain), never
  `io.github.*`; files are named after it. Why:
  [../phosh-toolkit/docs/decisions/domain-names.md](docs/decisions/domain-names.md).
- `.desktop` file: `X-Purism-FormFactor=Workstation;Mobile;` exactly,
  **including the trailing `;`**. Phosh's app grid hides an app in mobile
  mode unless this value contains the substring `mobile;`; the match is
  **case-insensitive** (`strcasestr` in `filter_adaptive()`,
  `src/app-grid.c`), so `Mobile;` works but `Workstation;Mobile` (no
  trailing `;`) does not. `desktop-file-validate` does not catch the
  missing `;`, so also check:

  ```sh
  grep -Eiq '^X-Purism-FormFactor=.*mobile;' path/to/*.desktop
  ```

  Details: [../phosh-toolkit/docs/phosh.md](docs/phosh.md).
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
  [../phosh-toolkit/docs/flatpak-workflow.md](docs/flatpak-workflow.md).
- Host setup: `bash ../phosh-toolkit/setup.sh` (Ubuntu 24.04, idempotent).

## Repositories and branches

- One repository per app; shared material lives in phosh-toolkit.
- Forks of third-party apps: work only on a branch named `phosh`. Keep
  `main` identical to upstream so upstream merges stay clean. Never commit
  Phosh changes to `main` of a fork.

## Knowledge

- Each repository keeps its knowledge in its own OKF v0.2 bundle: **the
  app's `docs/`** (entry point `docs/index.md` of the repository you are
  working in). Shared knowledge lives in `../phosh-toolkit/docs/` (entry
  point `../phosh-toolkit/docs/index.md`). Read both before starting work.
- Update the app's bundle **in the same commit** as the code change it
  describes: edit or add the concept file, update the app's
  `docs/index.md` when concepts are added or removed, and add an entry to
  the app's `docs/log.md`. Toolkit-wide findings go into a phosh-toolkit
  change instead.
- Never leave knowledge only in chat. Findings, decisions, workarounds and
  device facts go into `docs/` (the app's, or the toolkit's when shared).
- One file per concept with YAML frontmatter: `type` (required), `title`,
  `description`, `tags`, `resource` where applicable, `generated: { by,
  at }`, external facts in `sources` cited with `[^id]` footnotes. Agents
  use `<tool>/<version>` as actor; never write a `human:` actor in
  `verified` unless that person actually confirmed the content.
- New decisions go into the app's `docs/decisions/` as `type: Decision Record`.
- Cross-references are plain relative markdown links.

## Network access

- When a request to a host is blocked (proxy `403`, DNS failure, TLS
  refusal, tool error), tell the user **right away** which hosts are
  needed and why. Do not silently work around it or wait until the end
  of the task.
- List **only hosts you tested and found unreachable** (e.g.
  `curl -sS -m 15 -o /dev/null https://<host>/`), never hosts you merely
  expect to be blocked. Put them in a fenced code block, one host per
  line, without comments, so the user can paste it into the
  environment's allowed domains:

  ````
  ```
  opendata.dwd.de
  maps.dwd.de
  ```
  ````

  Explain what each host is for in the text outside the block.
- Then continue with the parts that do not need those hosts. Never
  replace blocked data with invented results.
- Record the required hosts in the app's `docs/` (e.g. a dev
  environment concept) so the next session knows them.

## Before committing

1. Build and run the tests of the touched project.
2. `appstreamcli validate` and `desktop-file-validate` if metadata changed.
3. `../phosh-toolkit/scripts/screenshot.sh` at 360×720 if the UI changed.
4. The app's `docs/` updated in the same commit.
5. Commit message and all texts in English.
