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

## Design

- Stock libadwaita look, following the GNOME HIG: no own theme, no
  branding, no overridden accent colour.
- Style classes before CSS (`suggested-action`, `boxed-list`, `card`,
  `title-1`…`4`, `heading`, `caption`, `dimmed`, `numeric`, `osd`). If CSS is
  unavoidable: colours only via `var(--…)` variables, one `style.css`
  resource per app, app-prefixed class names.
- No hard-coded colours or font sizes in UI chrome. Fixed colours are
  allowed only for data (radar scale) and never as the only carrier of
  information.
- Symbolic icons from the icon theme; icon-only buttons get a tooltip and
  an accessible label.
- Empty, error and offline states: `AdwStatusPage`, `AdwToast`,
  `AdwBanner`. Header capitalisation for titles and buttons, sentence
  capitalisation for descriptions.
- Full guideline and review checklist:
  [../phosh-toolkit/docs/design.md](docs/design.md).

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
    <control>pointing</control>
    <control>keyboard</control>
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

## Dependencies and licences

- Pin every dependency exactly; never float on "latest". Updates come as
  bot pull requests (update-check workflow, Dependabot). Every manifest
  source gets `x-checker-data`. See
  [../phosh-toolkit/docs/dependency-updates.md](docs/dependency-updates.md).
- Before adding a module: read its licence from the actual files, check
  it is compatible with the app's licence, list it in the app's
  `docs/dependencies.md`, and install its licence texts into
  `/app/share/licenses/<app id>/<module>/`. CI fails otherwise.
- Every repository is REUSE compliant (`REUSE.toml`, `LICENSES/`);
  third-party files in the repository get their real holder and licence.
- Data sources: follow and record their attribution rules, verified
  against the live terms. See
  [../phosh-toolkit/docs/licensing.md](docs/licensing.md).

## Repositories and branches

- One repository per app; shared material lives in phosh-toolkit.
- `main` is protected by the ruleset in `.github/rulesets/main.json`
  ([../phosh-toolkit/docs/branch-protection.md](docs/branch-protection.md)).
  When a CI job is renamed, update the required check names there in
  the same pull request and tell the owner to re-import it.
- Forks of third-party apps: work only on a branch named `phosh`. Keep
  `main` identical to upstream so upstream merges stay clean. Never commit
  Phosh changes to `main` of a fork.

## Shared code

- No copy-paste between apps. Code stays in an app until a second app
  needs it; then it moves into phosh-toolkit and both apps use it from
  there. Do not generalise code for one app in advance.
- Shared Python code lives in phosh-toolkit and is pulled into an app's
  Flatpak manifest pinned to a toolkit tag, never `main`.
- New apps start from the skeleton in `../phosh-toolkit/examples/`.
- Details:
  [../phosh-toolkit/docs/decisions/code-reuse.md](docs/decisions/code-reuse.md).

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
3. `../phosh-toolkit/scripts/screenshot.sh` at 360×720 if the UI changed,
   and the review checklist in
   [../phosh-toolkit/docs/design.md](docs/design.md).
4. No code duplicated from another app or from phosh-toolkit.
5. `reuse lint` passes; new modules are in `docs/dependencies.md`.
6. The app's `docs/` updated in the same commit.
7. Commit message and all texts in English.

## After the task: pull request and CI

The owner wants this done without being asked each time; it is a
standing instruction for every repository that imports this file.

1. When a task is done and pushed, open a pull request from the working
   branch into `main` (into `phosh` for forks) in **every repository the
   task changed**, unless one is already open for that branch. Title and
   body in English; the body says what changed, why, and how it was
   verified, and links the related pull requests in the other
   repositories.
2. Watch the CI of every pull request you opened until it finishes. On a
   failure: find the root cause, fix it, validate locally, push, and
   watch again until CI is green. Never skip or disable a check to get
   green.
3. A failure that is not caused by the pull request (red on `main` too,
   blocked host, missing secret): say so in a comment on the pull request
   and tell the user what is failing and what is needed.
4. Report to the user only when all pull requests are green, or what
   still blocks them, with links to the pull requests.
5. Do not merge; merging stays with the owner.
