---
type: Concept
title: Dependencies of the shared Flatpak modules
description: Inventory of the modules phosh-toolkit ships for app manifests (flatpak/) with version, licence and how they are kept current; the demo app builds them in the self-test.
tags: [dependencies, licences, flatpak, libshumate]
resource: ../flatpak/
generated: { by: claude-code/2.1.330, at: 2026-11-22T12:00:00Z }
sources:
  - id: protobuf-c
    resource: https://github.com/protobuf-c/protobuf-c/blob/v1.5.2/LICENSE
    title: protobuf-c 1.5.2, LICENSE (read 2026-11-22)
  - id: libshumate
    resource: https://github.com/GNOME/libshumate/blob/1.7.0/COPYING
    title: libshumate 1.7.0, COPYING and the license field of meson.build (GitHub mirror, read 2026-11-22)
---

# Modules

The modules in `flatpak/` that apps list in their manifests
([toolkit usage](toolkit-usage.md#3d-shared-flatpak-modules)). The demo
manifest `examples/de.nexumia.PhoshDemo.yml` includes them, so the
self-test builds them and the Flatpak workflow checks this inventory and
their licence files ([licensing](licensing.md)).

| Module | Version | Licence | File | Updates |
|---|---|---|---|---|
| `libshumate` | 1.7.0 | LGPL-2.1-or-later[^libshumate] | `flatpak/libshumate.yml` | GNOME checker, stable only |
| `protobuf-c` | 1.5.2 | BSD-2-Clause[^protobuf-c] | nested in `flatpak/libshumate.yml` | GitHub releases (JSON checker) |

Both are compatible with the apps' AGPL-3.0-or-later and the toolkit's
GPL-3.0-or-later. libshumate is LGPL: the Flatpak workflow publishes the
source bundle next to every app bundle. protobuf-c is built without
`protoc` (`--disable-protoc`); libshumate only needs the C runtime
library for vector tiles.

The versions are kept current by `.github/workflows/updates.yml` here
([dependency updates](dependency-updates.md)); apps get them with the
toolkit version their submodule points to.

[^libshumate]: libshumate 1.7.0, COPYING and meson.build
[^protobuf-c]: protobuf-c 1.5.2, LICENSE
