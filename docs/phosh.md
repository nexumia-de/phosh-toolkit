---
type: Platform
title: Phosh
description: The GNOME-based Wayland shell for phones that all apps target.
resource: https://phosh.mobi/
tags: [phosh, platform, mobile, gnome]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
stale_after: 2027-04-24T00:00:00Z
sources:
  - id: phosh-home
    resource: https://phosh.mobi/
    title: Phosh project website
  - id: phosh-repo
    resource: https://gitlab.gnome.org/World/Phosh/phosh
    title: Phosh source repository
  - id: phosh-app-grid
    resource: https://gitlab.gnome.org/World/Phosh/phosh/-/blob/main/src/app-grid.c
    title: Phosh app grid adaptive filter (filter_adaptive)
  - id: phoc-schema
    resource: https://gitlab.gnome.org/World/Phosh/phoc/-/tree/main/data
    title: phoc GSettings schema (scale-to-fit)
  - id: adw-adaptive
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/adaptive-layouts.html
    title: libadwaita adaptive layouts
---

# Overview

Phosh is a pure Wayland shell for mobile devices such as phones and small
tablets that use touch input, run on battery and have limited screen
space; it can also be docked to a keyboard and screen.[^phosh-repo] It is
built on GNOME technologies[^phosh-home] and developed in the GNOME
World/Phosh group, with [phoc](https://gitlab.gnome.org/World/Phosh/phoc)
as its companion compositor. It is shipped by phone distributions such as
postmarketOS, Mobian, PureOS and Fedora Mobility. The concrete distribution
and version used for testing is recorded in [device](device.md).

# Components

| Component      | Role                                                    |
|----------------|---------------------------------------------------------|
| phosh          | The shell: top bar, lock screen, app grid, overview.    |
| phoc           | The companion Wayland compositor (wlroots based).       |
| On-screen keyboard | [squeekboard](https://gitlab.gnome.org/World/Phosh/squeekboard) or [Stevia](https://gitlab.gnome.org/World/Phosh/stevia). |
| phosh-mobile-settings | Mobile specific settings (scaling, OSK, etc.).  |

# What it means for apps

- **Every toplevel window is maximized.** There is no free window
  placement; the app gets the whole screen minus the top bar. Design for
  the full 360 px width.
- **Logical size is about 360×720 px.** Typical phone panels are 720×1440
  at scale 2. The usable height shrinks further when the on-screen
  keyboard is open, so forms must scroll vertically.
- **Touch first.** No hover, no right-click by default; long-press opens
  context menus in GTK4. Targets must be large enough for a finger.
- **Desktop metadata decides visibility.** By default (`app-filter-mode`
  = `['adaptive']` in the `mobi.phosh.shell` schema) the app grid shows only
  adaptive apps in mobile mode. An app counts as adaptive if its `.desktop`
  file has `X-Purism-FormFactor` containing `mobile;` (case-insensitive,
  the trailing `;` is required) or `X-KDE-FormFactor` containing
  `handset;`, or if its id is listed in the `force-adaptive` key.[^phosh-app-grid]
  Use `X-Purism-FormFactor=Workstation;Mobile;`. Software centers also read
  the AppStream `display_length` and `control` relations in the metainfo
  (see [adaptive libadwaita](adaptive-libadwaita.md)).
- **Apps that do not fit** overflow the screen. phoc can optionally scale
  oversized windows down (`scale-to-fit`, off by default, globally or per
  app),[^phoc-schema] which makes them tiny and hard to use. A correctly
  adaptive app never needs this.

The UI rules derived from these constraints follow the libadwaita adaptive
layout guidance.[^adw-adaptive]

[^phosh-home]: Phosh project website
[^phosh-repo]: Phosh source repository
[^phosh-app-grid]: Phosh app grid adaptive filter (filter_adaptive)
[^phoc-schema]: phoc GSettings schema (scale-to-fit)
[^adw-adaptive]: libadwaita adaptive layouts
