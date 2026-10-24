# Directory Update Log

## 2026-10-24
* **Update**: Made the `X-Purism-FormFactor` rule exact in [Phosh](phosh.md) and [adaptive libadwaita](adaptive-libadwaita.md): case-insensitive substring match on `mobile;`, trailing `;` required, not caught by `desktop-file-validate`.
* **Update**: Documented the python3/python3-gi version mismatch handling in [screenshot testing](screenshot-testing.md).
* **Initialization**: Created the bundle with [device](device.md), [Phosh](phosh.md), [adaptive libadwaita](adaptive-libadwaita.md), [screenshot testing](screenshot-testing.md), [Flatpak workflow](flatpak-workflow.md), [toolkit usage](toolkit-usage.md) and the initial [decision records](decisions/).
* **Creation**: Added the demo app in `examples/` (verified with `scripts/screenshot.sh` at 360×720 and 800×600, and a local Flatpak build against GNOME 51).
