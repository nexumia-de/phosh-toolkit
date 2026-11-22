---
type: Playbook
title: Toolkit usage
description: How an app repository consumes phosh-toolkit for host setup, agent rules and Flatpak CI.
resource: https://github.com/nexumia-de/phosh-toolkit
tags: [toolkit, setup, agents, ci]
generated: { by: claude-code/2.1.310, at: 2026-10-24T22:30:00Z }
---

# Layout

The toolkit and every app repository are checked out side by side:

```
workspace/
  phosh-toolkit/        # this repository
  my-app/               # one repository per app
```

App repositories refer to the toolkit with the relative path
`../phosh-toolkit`. See the decisions on a
[central toolkit](decisions/central-toolkit.md) and
[one repository per app](decisions/one-repo-per-app.md).

# 1. Host setup

`setup.sh` installs the build stack on Ubuntu 24.04 and adds the Flathub
remote. It is idempotent and does not depend on any agent product.

In a cloud agent environment, put this in the environment setup script,
which runs in the directory above the repositories:

```sh
[ -d phosh-toolkit ] || git clone https://github.com/nexumia-de/phosh-toolkit.git
bash phosh-toolkit/setup.sh
```

On a laptop or VM, run the same two lines in the workspace directory.
`SKIP_FLATHUB=1` skips adding the Flathub remote; `SETUP_PROFILE=ci`
installs only the validation tools (see [host setup](host-setup.md)).

# 2. Agent rules

Each app repository has:

- `CLAUDE.md` containing only `@AGENTS.md`.
- `AGENTS.md` starting with the toolkit imports, followed by app-specific
  rules (repositories that are not GTK apps import only `agents/core.md`):

  ```markdown
  @../phosh-toolkit/agents/core.md
  @../phosh-toolkit/agents/gtk-app.md

  # My App

  App-specific rules only: what agents would get wrong without them
  ([lean agent rules](decisions/lean-agent-rules.md)).
  ```

Claude Code resolves the `@` import recursively; other agents read the
path in the prose. See the [AGENTS.md decision](decisions/agents-md.md).

# 3. Flatpak CI

`.github/workflows/flatpak.yml` in the app repository:

```yaml
name: Flatpak
on:
  push:
    branches: [main]
    tags: ['v*']
  pull_request:
  workflow_dispatch:
jobs:
  flatpak:
    permissions:
      contents: write
    uses: nexumia-de/phosh-toolkit/.github/workflows/flatpak.yml@<commit of the tag> # v0.7.0
    with:
      manifest: de.nexumia.MyApp.yml
```

Inputs: `manifest` (required), `bundle` (file name without extension,
defaults to the app id), `retention-days` (default 14),
`dependencies-doc` (licence inventory, default `docs/dependencies.md`,
see [licensing](licensing.md)), `metadata` (glob of the files the
Precheck job validates, default `data/*`; see
[precheck](flatpak-workflow.md#precheck-and-flatpak-ok)), `release`
(a tag `v<version>` attaches the bundles to its GitHub Release),
`nightly` (every push to `main` also builds `<app id>.Devel` and
attaches it to the pre-release `nightly`; see
[release channels](flatpak-workflow.md#release-channels)) and
`publish-repo` (repository to notify afterwards; needs the secret
`PUBLISH_TOKEN`). Details in the [Flatpak workflow](flatpak-workflow.md);
publishing to the phone through GNOME Software is described in
[shared app repository](app-repository.md).

Further inputs for the [release features](releases.md):
`release-config` (default `release.toml`). `toolkit-ref` (ref of the
toolkit scripts) is left out: the workflow uses the commit of its own
file.

## Pinning the toolkit

Apps call the reusable workflows at the commit of a toolkit tag, with
the tag as comment, like every other action
([decision](decisions/toolkit-version-pins.md)):

```yaml
    uses: nexumia-de/phosh-toolkit/.github/workflows/flatpak.yml@<commit of the tag> # v0.7.0
```

- The commit of a tag: `git ls-remote https://github.com/nexumia-de/phosh-toolkit refs/tags/v0.7.0`.
- All three workflows of an app (`flatpak.yml`, `release.yml`,
  `update-check.yml`) use the same commit. Nothing else names the
  version: the jobs check out the toolkit's scripts at
  `job.workflow_sha`, the commit of the workflow file that defines
  them.
- Dependabot's `github-actions` updates (already in every repository's
  `.github/dependabot.yml`) propose the next tag with SHA and comment;
  the app's CI then runs against it.
- `@main` still works and is what an app uses until its own pull request
  switches it; from then on a broken commit on the toolkit's `main`
  cannot break that app's CI or a running release.

For a fork of a third-party app, trigger the workflow on the `phosh`
branch instead of `main`.

# 3a. Releases

`release.toml`, `changelog.d/README.md` and
`.github/workflows/release.yml` calling
`nexumia-de/phosh-toolkit/.github/workflows/release.yml@<commit of the tag>` (the usage
block at the top of that file), plus the secret `RELEASE_TOKEN` and the
required check `release / Changelog` in the app's ruleset. See
[releases](releases.md).

# 3b. Updates and licences

- `.github/workflows/update-check.yml` calling
  `nexumia-de/phosh-toolkit/.github/workflows/update-check.yml@<commit of the tag>`
  weekly, and `.github/dependabot.yml` for GitHub Actions. Setup steps:
  [dependency updates](dependency-updates.md).
- `REUSE.toml` and `LICENSES/`, `docs/dependencies.md`, and licence
  installs for every manifest module: [licensing](licensing.md).

# 3c. Shared Python package

Runtime code that two apps need lives in `lib/phosh_toolkit/`
([code reuse](decisions/code-reuse.md)); what it contains is in
[shared connection and playback](shared-connection.md). An app pulls it
into its Flatpak as a module **before** the app module, pinned to a
toolkit tag and its commit. A new tag comes from the manual workflow
*Tag release* (`.github/workflows/tag-release.yml`, input `version`
such as `0.4.0`), which tags the current `main`; tags made by hand
(`git tag v0.4.0 && git push origin v0.4.0`) work the same.

```yaml
modules:
  - name: phosh-toolkit
    buildsystem: simple
    build-commands:
      - install -Dm644 -t "$(python3 -c 'import sysconfig; print(sysconfig.get_path("purelib", vars={"base":"/app"}))')/phosh_toolkit" lib/phosh_toolkit/*.py
      - install -Dm644 -t /app/share/licenses/$FLATPAK_ID/phosh-toolkit LICENSE
    sources:
      - type: git
        url: https://github.com/nexumia-de/phosh-toolkit.git
        tag: v0.1.0
        commit: <commit of the tag>
        x-checker-data:
          type: git
          tag-pattern: ^v([\d.]+)$
  - name: my-app
    ...
```

The files land in the runtime Python's `site-packages` under `/app`,
which is also where meson installs the app's own package, so the app's
launcher finds both. List the module as `` `phosh-toolkit` `` in the
app's `docs/dependencies.md` (GPL-3.0-or-later, compatible with the
apps' AGPL-3.0-or-later).

From the source tree and in the app's test job the package comes from
the sibling checkout: `PYTHONPATH=../phosh-toolkit/lib`. The app's
`tests.yml` checks out phosh-toolkit at the commit the manifest pins,
so tests and Flatpak use the same code.

# 3d. Shared Flatpak modules

Manifest modules that two apps need live in `flatpak/`
([decision](decisions/shared-flatpak-modules.md),
[inventory](dependencies.md)):

| File | Modules | For |
|---|---|---|
| `flatpak/libshumate.yml` | `libshumate`, nested `protobuf-c` | apps with a map |

flatpak-builder includes module files only from the app's own tree, so
the app adds the toolkit as a git submodule (the way Flathub's
`shared-modules` is used) at the same tag its `phosh-toolkit` module
pins:

```sh
git submodule add https://github.com/nexumia-de/phosh-toolkit.git toolkit
```

```sh
git -C toolkit checkout v0.7.0
```

```yaml
modules:
  - toolkit/flatpak/libshumate.yml
  - name: phosh-toolkit
    ...
```

- The Flatpak workflow checks submodules out (`submodules: recursive`)
  and `--show-manifest` inlines the file, so the dependency inventory
  check, the licence file check and the Flathub manifest see the
  modules like any other. List `` `libshumate` `` and `` `protobuf-c` ``
  in the app's `docs/dependencies.md`.
- `REUSE.toml` of the app: REUSE skips submodules by default; nothing
  to add.
- Versions are updated here (`.github/workflows/updates.yml`), not in
  the app: when the app moves to a new toolkit tag, change the
  submodule and the `tag`/`commit` of the `phosh-toolkit` module in the
  same pull request.
- The file sets no `cleanup`; the app's manifest removes headers and
  static libraries as before (`/include`, `/lib/pkgconfig`,
  `/share/gir-1.0`, `'*.a'`, `'*.la'`).

# 4. Screenshots

From the app repository:

```sh
../phosh-toolkit/scripts/screenshot.sh -o shot.png -- <command>
```

See [screenshot testing](screenshot-testing.md). Screenshots for the
metainfo and the release are declared in `release.toml` and taken by CI;
see [releases](releases.md).

# 5. Knowledge

Each app repository keeps its own OKF bundle in `docs/` with the same
conventions as this one (see the [OKF decision](decisions/okf-docs.md)).
Toolkit-wide knowledge goes into this bundle instead.
