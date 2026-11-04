---
type: Guideline
title: Adaptive libadwaita UI
description: Rules for GTK4/libadwaita UIs that work at 360×720 on Phosh and scale up to the desktop.
tags: [ui, gtk4, libadwaita, adaptive, guideline]
generated: { by: claude-code/2.1.317, at: 2026-11-04T00:30:00Z }
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
  - id: adw-navview-src
    resource: https://gitlab.gnome.org/GNOME/libadwaita/-/blob/main/src/adw-navigation-view.c
    title: libadwaita adw-navigation-view.c (gestures, can-pop; read 2026-11-04 from the GitHub mirror)
  - id: adw-splitview-src
    resource: https://gitlab.gnome.org/GNOME/libadwaita/-/blob/main/src/adw-navigation-split-view.c
    title: libadwaita adw-navigation-split-view.c (collapsed child is a navigation-view)
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
9. **Swipe back everywhere.** Every page the user opens from another
   page closes with a smooth swipe from left to right, which follows the
   finger and snaps back if let go early. Ephyra does this on every
   page; it is the owner's requirement for all apps (2026-11-04).
   - **How:** it comes for free from `AdwNavigationView` (and the
     collapsed `AdwNavigationSplitView`, whose child then is an
     `AdwNavigationView`): one-finger swipe to the right on touchscreens,
     two-finger swipe on touchpads, Alt+←, the back mouse button and
     Escape all pop the page with the same animation.[^adw-navview-src][^adw-splitview-src]
     So every "open something, then go back" relation is a page *pushed*
     onto a navigation view (`push`, or a split view's content). Never
     switch pages of a `GtkStack`/`AdwViewStack` and draw an own back
     button: that has no gesture. View stacks are only for peer views
     (tabs), which have no "back".
   - **Direction matters.** Only pages above another one can be swiped
     away. In a collapsed split view the *sidebar is the root*: a view
     that a button opens must not be the sidebar shown by
     `show-content = false`, or the user lands on a page with nothing
     to swipe back to (Cirro's places list, nexumia-de/cirro#50). Push
     such a view as its own page, or make it the content.
   - **Keep `can-pop` true.** `AdwNavigationPage:can-pop = false`
     disables the gesture and the back button[^adw-navview-src]; use it
     only where leaving would lose work, and ask in an
     `AdwAlertDialog` instead where possible.
   - **Widgets that take horizontal drags** (maps, sliders, horizontal
     scrolling) can keep the gesture from starting on top of them. Check
     on the phone that a page with such a widget still swipes back from
     its header bar or another free area, and record the result in the
     app's `docs/`.
   - **Verify** on the phone (label the issue `on device`): every pushed
     page swipes back, the animation follows the finger, and letting go
     early snaps back. Screenshots can't show gestures.
10. **Verify** every UI change with `scripts/screenshot.sh` at 360×720 and
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
  <control>pointing</control>
  <control>keyboard</control>
  <control>touch</control>
</supports>
```

List every input method the app handles, not only `touch`. Once an app
declares any `<control>`, GNOME Software treats the unlisted ones as
unsupported and shows "Keyboard not supported" and "Mouse not supported"
on the app page. Every app here must also work as a desktop window, so
`pointing` and `keyboard` belong in `<supports>` as well.

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
[^adw-navview-src]: libadwaita adw-navigation-view.c
[^adw-splitview-src]: libadwaita adw-navigation-split-view.c
[^as-relations]: AppStream relations (requires, recommends, supports)
