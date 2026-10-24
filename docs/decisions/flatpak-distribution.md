---
type: Decision Record
title: Flatpak as distribution format
description: Apps ship as Flatpak bundles built for x86_64 and aarch64 against the GNOME runtime.
tags: [decision, flatpak, distribution]
generated: { by: claude-code/2.1.310, at: 2026-10-24T19:26:02Z }
---

# Status

Accepted (2026-10-24).

# Context

The target [device](../device.md) runs [Phosh](../phosh.md) on some phone
distribution whose package versions differ from the development host
(Ubuntu 24.04). Native packages would need one packaging effort per
distribution, and host libraries (e.g. libadwaita 1.5 on Ubuntu 24.04) lag
behind current GNOME.

# Decision

Every app is distributed as a Flatpak using `org.gnome.Platform` from
Flathub. CI builds bundles for x86_64 and aarch64 with the reusable
workflow (see [Flatpak workflow](../flatpak-workflow.md)).

# Consequences

- One build works on every distribution that has Flatpak.
- Apps get the current libadwaita of the GNOME runtime.
- Sandbox permissions (`finish-args`) must be declared and kept minimal.
- The phone needs the Flathub remote to install the runtime.
