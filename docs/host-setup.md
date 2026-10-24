---
type: Tool
title: Host setup
description: What setup.sh installs in its full and ci profiles, why weston was replaced by cage, and how apt is hardened against stalls.
resource: ../setup.sh
tags: [setup, apt, ci, ubuntu]
generated: { by: claude-code/2.1.310, at: 2026-10-24T21:30:00Z }
---

# Usage

```sh
bash ../phosh-toolkit/setup.sh                    # full profile (default)
SETUP_PROFILE=ci bash ../phosh-toolkit/setup.sh   # lean profile for CI validation
SKIP_FLATHUB=1 bash ../phosh-toolkit/setup.sh     # full, without the Flathub remote
```

The script is idempotent: it installs only missing packages and adds the
Flathub remote only once. Unknown profiles fail with an error.

# Profiles

| Profile | For | Contents | Fresh-system size* |
|---------|-----|----------|--------------------|
| `full`  | Dev sessions, laptops, VMs | Build tools, GTK4/libadwaita dev packages, Blueprint, Vala, Rust, PyGObject, Flatpak + flatpak-builder, `cage`, validators, shellcheck; adds Flathub | 491 packages, 340 MB |
| `ci`    | The `validate` job in `selftest.yml` | `desktop-file-utils`, `appstream`, `librsvg2-common`, `libgtk-4-bin`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`, `python3-gi`, `shellcheck`; no Flatpak, no Flathub | 205 packages, 73 MB |

\*Download size with `--no-install-recommends` from an empty dpkg status
(`apt-get install -s -o Dir::State::status=<empty file>`), measured
2026-10-24 on Ubuntu 24.04. A GitHub runner already has many of these
packages, so it installs fewer.

The Flatpak build jobs do not use `setup.sh`; the reusable workflow
installs only `flatpak`, `flatpak-builder` and `librsvg2-common` (see
[Flatpak workflow](flatpak-workflow.md)).

# Why cage instead of weston

The full profile used to install `weston` as a test compositor. Nothing
in the toolkit uses it: screenshots go through Broadway (see
[screenshot testing](screenshot-testing.md)). Weston was by far the
heaviest package. On top of the rest of the full profile it added
**112 packages / 72 MB**, including the whole FFmpeg stack. The dependency
chain (Depends only, as installed with `--no-install-recommends`):

```
weston -> libweston-13-0 -> libneatvnc0 -> libavcodec60
weston -> libweston-13-0 -> libneatvnc0 -> libavfilter9 -> libflite1
```

libweston links its VNC (neatvnc → FFmpeg), RDP (FreeRDP) and PipeWire
remoting backends, which bring in libavcodec/libavformat/libavfilter,
x264/x265/svt-av1/dav1d/aom, GStreamer, PipeWire, flite and pocketsphinx.
A CI run stalled for 15 minutes downloading `libflite1` (13.6 MB) from
`azure.archive.ubuntu.com` until the job timeout cancelled it.

`cage` (a wlroots kiosk compositor) adds only 32 packages / 3 MB and runs
headless. Like Phosh, it shows one maximized window:

```sh
export XDG_RUNTIME_DIR=$(mktemp -d)
WLR_BACKENDS=headless WLR_RENDERER=pixman WLR_LIBINPUT_NO_DEVICES=1 \
  cage -- env GDK_BACKEND=wayland GSK_RENDERER=cairo <command>
```

Verified 2026-10-24 with `examples/adw-demo.py`: GTK used the Wayland
backend and the window was mapped at the full 1280×720 headless output.
Without GPU access, `GSK_RENDERER=cairo` is needed or the window never maps.

# apt hardening

All apt calls run as:

```sh
sudo env DEBIAN_FRONTEND=noninteractive apt-get \
  -o DPkg::Lock::Timeout=120 -o Acquire::Retries=3 -o Acquire::http::Timeout=30
```

- `sudo env …`: sudo resets the environment, so an exported
  `DEBIAN_FRONTEND` would never reach apt.
- `DPkg::Lock::Timeout=120`: wait at most 2 minutes for a lock held by
  e.g. unattended-upgrades.
- `Acquire::http::Timeout=30` and `Acquire::Retries=3`: a connection that
  stalls for 30 s is dropped and the download retried, instead of hanging
  until the job timeout.

# CI history of the validate job's "Set up host" step

| Run | Profile | Duration | Note |
|-----|---------|----------|------|
| 1–3, 5, 6 | full (`SKIP_FLATHUB=1`) | 28–57 s | normal mirror speed |
| 4 | full | 19 min 39 s | mirror at 144 kB/s |
| 7 | full | cancelled at 15 min 09 s | stalled on `libflite1` |
| this change | ci | see the PR | |
