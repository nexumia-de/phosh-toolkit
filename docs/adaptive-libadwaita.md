---
type: Guideline
title: Adaptive libadwaita UI
description: Rules for GTK4/libadwaita UIs that work at 360×720 on Phosh and scale up to the desktop.
tags: [ui, gtk4, libadwaita, adaptive, guideline]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:05:00Z }
sources:
  - id: adw-adaptive
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/adaptive-layouts.html
    title: libadwaita adaptive layouts
  - id: adw-breakpoint
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/class.Breakpoint.html
    title: AdwBreakpoint API reference
  - id: adw-migrate
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/migrating-to-breakpoints.html
    title: libadwaita migrating to breakpoints
  - id: as-relations
    resource: https://www.freedesktop.org/software/appstream/docs/chap-Metadata.html#tag-relations
    title: AppStream relations (requires, recommends, supports)
---

# Target

[Phosh](phosh.md) on the [target phone](device.md): **360×720 logical px**,
touch, aarch64, window always maximized. The same app must also work as a
normal desktop window. Visual styling (colours, typography, icons, text)
is covered by [visual design](design.md).

# Rules

1. **No horizontal scrolling at 360 px.** Every view must fit 360 px wide.
   Use `hscrollbar-policy: never` on scrolled windows, let labels wrap or
   ellipsize, and never set fixed widths larger than 360.
2. **Minimum size 360×294.** Breakpoints only work when the window has a
   minimum size, and the content must fit into it.[^adw-migrate] Call
   `set_size_request(360, 294)` (or set `width-request`/`height-request`)
   on the main window.
3. **Use `AdwBreakpoint` for layout changes.**[^adw-breakpoint] Conditions use
   `sp` units. The upstream examples use `max-width: 400sp` to collapse
   split views and `max-width: 550sp` to swap a header `AdwViewSwitcher`
   for a bottom `AdwViewSwitcherBar`.[^adw-adaptive]
4. **Navigation:** `AdwNavigationSplitView` for sidebar + content (it
   collapses into an `AdwNavigationView` with back button),
   `AdwOverlaySplitView` for a utility pane, `AdwNavigationView` for
   drill-down flows.[^adw-adaptive]
5. **Structure each page as `AdwToolbarView`** with `AdwHeaderBar` on top
   and optional bottom bars. Keep header bars short: at 360 px there is
   room for a title and about two buttons per side.
6. **Content width:** wrap forms and text in `AdwClamp` so they look right
   on the desktop and fill the phone. Use boxed lists (`AdwActionRow`,
   `AdwEntryRow`, `AdwSwitchRow`, `AdwComboRow`) instead of grids of
   labels and inputs.
7. **Dialogs:** use `AdwDialog` / `AdwAlertDialog` (libadwaita ≥ 1.5); they
   become bottom sheets on narrow windows. Avoid `GtkDialog` and separate
   toplevel windows.
8. **Touch:** no hover-only affordances, every context menu reachable via
   a visible button or long-press, targets not smaller than the default
   libadwaita button height. Leave space for the on-screen keyboard: forms
   must scroll vertically.
9. **Verify** every UI change with `scripts/screenshot.sh` at 360×720 and
   at a desktop size (see [screenshot testing](screenshot-testing.md)).

# libadwaita versions

| Widget                                     | Since |
|--------------------------------------------|-------|
| `AdwBreakpoint`, `AdwNavigationSplitView`, `AdwToolbarView` | 1.4 |
| `AdwDialog`, `AdwAlertDialog`              | 1.5   |
| `AdwBottomSheet`, `AdwMultiLayoutView`     | 1.6   |

Flatpak builds use the libadwaita of the GNOME runtime, so the newest
widgets are available there. Host builds on Ubuntu 24.04 have 1.5 only.

# Required metadata

`.desktop` file:

```ini
X-Purism-FormFactor=Workstation;Mobile;
```

The trailing `;` is required: Phosh matches the case-insensitive substring
`mobile;` and hides the app in mobile mode otherwise (see
[Phosh](phosh.md)). `desktop-file-validate` does not catch a missing `;`,
so also run `grep -Eiq '^X-Purism-FormFactor=.*mobile;' data/*.desktop`.

AppStream metainfo:[^as-relations]

```xml
<recommends>
  <display_length compare="ge">360</display_length>
</recommends>
<supports>
  <control>touch</control>
</supports>
```

Validate both before every commit:

```sh
desktop-file-validate data/*.desktop
appstreamcli validate data/*.metainfo.xml
```

A complete working example is the demo app in
[`examples/`](../examples/): `adw-demo.py`, its `.desktop` file and its
metainfo.

# Examples

```python
split = Adw.NavigationSplitView(sidebar=sidebar_page, content=content_page)
window.set_content(split)
bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 400sp"))
bp.add_setter(split, "collapsed", True)
window.add_breakpoint(bp)
```

Blueprint:

```blueprint
Adw.Breakpoint {
  condition ("max-width: 400sp")
  setters {
    split_view.collapsed: true;
  }
}
```

[^adw-adaptive]: libadwaita adaptive layouts
[^adw-breakpoint]: AdwBreakpoint API reference
[^adw-migrate]: libadwaita migrating to breakpoints
[^as-relations]: AppStream relations (requires, recommends, supports)
