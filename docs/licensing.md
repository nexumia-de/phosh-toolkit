---
type: Guideline
title: Licensing
description: How the repositories declare their own licences (REUSE) and how apps meet the licence terms of everything they bundle or display.
tags: [licensing, reuse, flatpak, attribution, guideline]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
sources:
  - id: reuse
    resource: https://reuse.software/spec-3.3/
    title: REUSE Specification 3.3
  - id: fb-news
    resource: https://github.com/flatpak/flatpak-builder/blob/main/NEWS
    title: flatpak-builder NEWS (1.4.5 license-files)
  - id: fb-module
    resource: https://github.com/flatpak/flatpak-builder/blob/main/src/builder-module.c
    title: flatpak-builder builder-module.c (licence install path)
---

# Three layers

1. **Own code**: every file has a licence, declared with REUSE.
2. **Bundled code**: every module in the Flatpak is listed with its
   licence, its licence texts ship in the bundle, and the corresponding
   source is published.
3. **Data and services**: attribution as each source requires, in the UI
   next to the data and in the About dialog.

CI enforces 1 and the mechanical part of 2 through the reusable
[Flatpak workflow](flatpak-workflow.md).

# 1. Own code: REUSE

Each repository is REUSE compliant:[^reuse]

- `REUSE.toml` assigns copyright and licence to paths (`**` for the
  default, overrides for exceptions such as CC0 metainfo or third-party
  sample data). No per-file headers needed.
- `LICENSES/<SPDX-id>.txt` holds every licence text used
  (`reuse download --all`). The root `LICENSE` stays for GitHub's licence
  detection.
- Third-party files inside the repository (recorded sample data, copied
  snippets) get their own annotation with the real copyright holder and
  licence.
- `reuse lint` runs in the `reuse` job of the Flatpak workflow.

Licences in use: phosh-toolkit `GPL-3.0-or-later`, apps as decided per
app (Cirro `AGPL-3.0-or-later`); AppStream metadata `CC0-1.0`, matching
`metadata_license` in the metainfo.

# 2. Bundled code

## Inventory

Every module of the app's manifest except the app itself is listed in
the app's `docs/dependencies.md` with version, SPDX licence expression,
libraries it bundles itself (wheels often do) and how updates are found.
CI fails when a module is missing there.

Before adding a module, check that its licence is compatible with the
app's licence and record it. Read the licence from the actual files
(tarball `COPYING`/`LICENSE`, wheel `METADATA` `License-Expression` and
`dist-info/licenses/`, `*.libs/` for bundled shared libraries), not from
memory.

## Licence texts in the bundle

BSD/MIT-style licences require the licence text in binary
distributions. Every module installs its texts into
`/app/share/licenses/<app id>/<module name>/`; CI fails if that directory
is empty for any module.

- flatpak-builder 1.4.5 and later do this automatically and offer a
  `license-files` property,[^fb-news] using exactly this
  path.[^fb-module] Ubuntu 24.04 (CI and host) ships 1.4.2, which does
  neither, so install the files explicitly:

  ```yaml
  # autotools/simple modules build in the source directory
  post-install:
    - install -Dm644 LICENSE -t ${FLATPAK_DEST}/share/licenses/${FLATPAK_ID}/protobuf-c
  # meson/cmake modules build in _flatpak_build/
  post-install:
    - install -Dm644 ../COPYING -t ${FLATPAK_DEST}/share/licenses/${FLATPAK_ID}/libshumate
  # wheels: copy the dist-info licence tree
  build-commands:
    - pip3 install … --no-deps numpy
    - install -d ${FLATPAK_DEST}/share/licenses/${FLATPAK_ID}
    - cp -r ${FLATPAK_DEST}/lib/python3*/site-packages/numpy-*.dist-info/licenses ${FLATPAK_DEST}/share/licenses/${FLATPAK_ID}/python3-numpy
  ```

- When a wheel bundles a library without its licence text, add the text
  as an extra `type: file` source from the upstream tag and install it
  (Cirro does this for libaec inside h5py).

## Corresponding source

For (L)GPL components distributed as binaries, the source must be
available. The Flatpak workflow builds with `--bundle-sources` and
publishes `<bundle>-sources-<arch>.flatpak` (runtime `<app id>.Sources`,
all sources of the build) next to the app bundle; phosh-apps imports it
into the repository, as Flathub does. Binary-only parts inside wheels
(for example GCC runtime libraries) are named in the app's
`docs/dependencies.md` with where their source is.

## About dialog

List the bundled libraries in `AdwAboutDialog` with
`add_legal_section()` (name, copyright holder, licence) and say that the
full texts are in `/app/share/licenses/<app id>/`.

# 3. Data and services

- Follow each provider's attribution rules exactly and record them,
  verified against the live terms, in the app's docs (Cirro:
  `docs/data-sources.md`, section on licences and attribution).
- Attribution goes next to the data (map overlay, chart caption) and into
  the About dialog. Keep the on-screen text short enough for 360 px; put
  the long form in the About dialog when the provider allows it.
- OSM: "© OpenStreetMap contributors" with a link to
  `https://www.openstreetmap.org/copyright`.
- Never use a provider's logo or brand in the UI or metadata unless the
  app's rules allow it.

[^reuse]: REUSE Specification 3.3
[^fb-news]: flatpak-builder NEWS (1.4.5 license-files)
[^fb-module]: flatpak-builder builder-module.c (licence install path)
