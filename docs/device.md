---
type: Device
title: Target phone
description: The physical phone the apps are developed and tested for; placeholder until the owner fills in the details.
tags: [device, hardware, target]
status: draft
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
---

# Summary

All apps target a phone running [Phosh](phosh.md) with a logical
resolution of **360×720 px**, touch input and an **aarch64** CPU. The
values below marked `TODO` must be filled in by the device owner; until
then, design against the generic target.

# Hardware

| Property                | Value                         |
|-------------------------|-------------------------------|
| Model                   | TODO                          |
| SoC / CPU architecture  | TODO / aarch64                |
| RAM                     | TODO                          |
| Physical resolution     | TODO (e.g. 720×1440)          |
| Display scale           | TODO (e.g. 2)                 |
| Logical resolution      | 360×720 (assumed)             |
| Input                   | Touch, on-screen keyboard     |

# Software

| Property            | Value |
|---------------------|-------|
| OS / distribution   | TODO  |
| Kernel              | TODO  |
| Phosh version       | TODO  |
| phoc version        | TODO  |
| libadwaita (host)   | TODO  |
| Flatpak version     | TODO  |

# How to collect the values

Run on the phone and paste the results into the tables above:

```sh
cat /etc/os-release
uname -rm
flatpak --version
# Debian/Mobian/PureOS: dpkg -l phosh phoc libadwaita-1-0
# postmarketOS/Alpine:  apk info -v phosh phoc libadwaita
wlr-randr            # physical mode and scale of the built-in display
```

After filling it in, set `status: stable`, update `generated`, and add a
`verified: { by: human:suitably, at: ... }` entry.
