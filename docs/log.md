# Directory Update Log

## 2026-10-24
* **Creation**: [Host setup](host-setup.md): `SETUP_PROFILE=ci` lean profile for the validate job, `cage` replaces `weston` (whose VNC/RDP backends pulled in FFmpeg and flite), apt retries stalled downloads.
* **Update**: CI hardening in [Flatpak workflow](flatpak-workflow.md): job timeouts (validate 15 min, Flatpak build 30 min), apt with `DEBIAN_FRONTEND` passed through `sudo env` and a 120 s dpkg lock timeout, in `setup.sh` and the workflow.
* **Update**: Root [index](index.md) links [decisions/index.md](decisions/index.md) instead of the directory. The Flatpak CI cache key no longer includes the commit SHA (see [Flatpak workflow](flatpak-workflow.md)).
* **Update**: [Flatpak workflow](flatpak-workflow.md): `librsvg2-common` is required for `appstreamcli compose` to read SVG icons (x86_64 CI failed without it).
* **Update**: [Screenshot testing](screenshot-testing.md) now resolves Playwright from the caller's directory, so a local `node_modules` works (it failed in CI before).
* **Update**: Made the `X-Purism-FormFactor` rule exact in [Phosh](phosh.md) and [adaptive libadwaita](adaptive-libadwaita.md): case-insensitive substring match on `mobile;`, trailing `;` required, not caught by `desktop-file-validate`.
* **Update**: Documented the python3/python3-gi version mismatch handling in [screenshot testing](screenshot-testing.md).
* **Initialization**: Created the bundle with [device](device.md), [Phosh](phosh.md), [adaptive libadwaita](adaptive-libadwaita.md), [screenshot testing](screenshot-testing.md), [Flatpak workflow](flatpak-workflow.md), [toolkit usage](toolkit-usage.md) and the initial [decision records](decisions/index.md).
* **Creation**: Added the demo app in `examples/` (verified with `scripts/screenshot.sh` at 360×720 and 800×600, and a local Flatpak build against GNOME 51).
