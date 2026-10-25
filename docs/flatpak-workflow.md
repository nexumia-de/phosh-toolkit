---
type: Playbook
title: Flatpak build and install workflow
description: How to build Flatpak bundles locally and in CI for x86_64 and aarch64, and install them on the phone.
resource: ../.github/workflows/flatpak.yml
tags: [flatpak, build, ci, install, aarch64]
generated: { by: claude-code/2.1.310, at: 2026-10-24T22:30:00Z }
sources:
  - id: flatpak-builder
    resource: https://docs.flatpak.org/en/latest/flatpak-builder.html
    title: Flatpak documentation, flatpak-builder
  - id: flatpak-bundles
    resource: https://docs.flatpak.org/en/latest/single-file-bundles.html
    title: Flatpak documentation, single-file bundles
---

# Overview

Every app ships as a Flatpak (see the
[decision record](decisions/flatpak-distribution.md)). Each app repository
contains a manifest named after its app id, e.g.
`de.nexumia.MyApp.yml`, using the GNOME runtime from Flathub.

# Manifest conventions

- `runtime: org.gnome.Platform`, `sdk: org.gnome.Sdk`, current stable
  `runtime-version` (51 as of 2026-10). Bump it together with all apps.
- `finish-args`: `--share=ipc`, `--socket=wayland`,
  `--socket=fallback-x11`, `--device=dri`; add more only when needed and
  explain why in the app's docs.
- Install the `.desktop` file, metainfo and icon under the app id.
- A minimal working manifest is
  [`examples/de.nexumia.PhoshDemo.yml`](../examples/de.nexumia.PhoshDemo.yml).

# Local build (x86_64)

```sh
flatpak-builder --user --install-deps-from=flathub --force-clean \
  --install build-dir de.nexumia.MyApp.yml
flatpak run de.nexumia.MyApp
```

`setup.sh` adds the Flathub remote **system-wide**. For `--user` builds
also add it for the user:
`flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`.
Without `--user`, flatpak-builder installs dependencies system-wide.[^flatpak-builder]

Inside containers without FUSE, add `--disable-rofiles-fuse`.

flatpak-builder runs `appstreamcli compose` on the host. It needs the SVG
gdk-pixbuf loader from `librsvg2-common` to read SVG icons. That package
is only a Recommends of the appstream stack, so with
`--no-install-recommends` the build fails with `file-read-error` and
`filters-but-no-output`. `setup.sh` and the reusable workflow install it
explicitly.

The same applies to `elfutils`: flatpak-builder strips every ELF file a
module installs with `eu-strip`. Without it, the first module with
compiled code fails with `Failed to execute child process "eu-strip"`.
Apps that only install scripts (like the demo) never hit this. `setup.sh`
and the reusable workflow install it explicitly.

# Bundle

```sh
flatpak-builder --repo=repo --force-clean build-dir de.nexumia.MyApp.yml
flatpak build-bundle repo MyApp.flatpak de.nexumia.MyApp \
  --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo
```

`--runtime-repo` lets the phone fetch the GNOME runtime from Flathub when
installing the bundle.[^flatpak-bundles]

# CI build (x86_64 and aarch64)

App repositories call the reusable workflow; see
[toolkit usage](toolkit-usage.md). It builds natively on `ubuntu-24.04`
(x86_64) and `ubuntu-24.04-arm` (aarch64), installs `flatpak` and
`flatpak-builder` from apt, lifts Ubuntu's AppArmor restriction on
unprivileged user namespaces (needed by bubblewrap), caches
`.flatpak-builder` (one cache entry per architecture and manifest hash;
it is refreshed when the manifest changes) and uploads `<bundle>-<arch>.flatpak` as an artifact
named `<bundle>-<arch>`. The build job has `timeout-minutes: 30`; apt
runs with `DEBIAN_FRONTEND=noninteractive` passed through `sudo env` (sudo
drops exported variables) and `-o DPkg::Lock::Timeout=120`. Slow runner
mirrors happen: one run fetched 166 MB at 144 kB/s and took 19 minutes, so
a timeout fails such a run fast instead of letting it run for 6 hours.
Cross-building aarch64 locally under QEMU works
but is slow; prefer CI.

# Release for the shared repository

With `release: true`, a push additionally runs the job *Release
bundles*: it downloads both artifacts and attaches them to the rolling
GitHub Release `latest` (created on the first run, its tag moved to the
pushed commit afterwards, assets replaced with `--clobber`). The caller
must grant `permissions: { contents: write }` to the job. With
`publish-repo` and the secret `PUBLISH_TOKEN` it then sends
`repository_dispatch` `app-updated` to that repository; without the
token it logs a notice and the publish repository's daily run picks the
release up. See [shared app repository](app-repository.md).

# Install on the phone

The normal way is GNOME Software through the
[shared app repository](app-repository.md). For testing a single build:

1. Download the `<bundle>-aarch64` artifact from the workflow run (GitHub
   delivers it as a zip) and unzip it.
2. Copy it to the phone: `scp MyApp-aarch64.flatpak phone:`
3. On the phone:

   ```sh
   flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
   flatpak install --user ./MyApp-aarch64.flatpak
   flatpak run de.nexumia.MyApp
   ```

4. Updating: install the newer bundle the same way; `flatpak uninstall
   de.nexumia.MyApp` removes it.

[^flatpak-builder]: Flatpak documentation, flatpak-builder
[^flatpak-bundles]: Flatpak documentation, single-file bundles
