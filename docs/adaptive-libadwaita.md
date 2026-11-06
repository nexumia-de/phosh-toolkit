---
type: Guideline
title: Adaptive libadwaita UI
description: Rules for GTK4/libadwaita UIs that work at 360×720 on Phosh and scale up to the desktop.
tags: [ui, gtk4, libadwaita, adaptive, guideline]
generated: { by: claude-code/2.1.318, at: 2026-11-05T07:30:00Z }
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
  - id: hig-adaptive
    resource: https://developer.gnome.org/hig/guidelines/adaptive.html
    title: GNOME HIG – Scaling & adaptiveness (read 2026-11-05)
  - id: hig-pointer-touch
    resource: https://developer.gnome.org/hig/guidelines/pointer-touch.html
    title: GNOME HIG – Pointer and touch input (read 2026-11-05)
  - id: hig-header-bars
    resource: https://developer.gnome.org/hig/patterns/containers/header-bars.html
    title: GNOME HIG – Header bars (read 2026-11-05)
  - id: hig-view-switchers
    resource: https://developer.gnome.org/hig/patterns/nav/view-switchers.html
    title: GNOME HIG – View switchers (read 2026-11-05)
  - id: hoober
    resource: https://www.uxmatters.com/mt/archives/2013/11/design-for-fingers-and-thumbs-instead-of-touch.php
    title: Steven Hoober, Design for Fingers and Thumbs Instead of Touch (UXmatters, 2013)
  - id: wcag-target
    resource: https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html
    title: WCAG 2.2 – 2.5.5 Target Size (Enhanced), 44 × 44 CSS px
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
   - **Sidebar plus drill-down pages: Ephyra's layout.** One
     `AdwNavigationView` per window. Its first page holds an
     `AdwNavigationSplitView` (sidebar page and content page), collapsed
     by an `AdwBreakpoint` below 600 sp; choosing an entry in the
     sidebar sets the content and `show-content = true`. Collapsed, the
     content lies above the sidebar, so a swipe goes back to it. Every
     page opened from the content (details, a task, search) is pushed
     on the outer navigation view (Ephyra's `window.py` and
     `browse.py`; Pensum the same way). Nauta has no sidebar: tabs
     (`AdwViewStack` with a view switcher) on the first page, everything
     else pushed on top. The owner uses Ephyra and Nauta on the phone as
     the reference for the back swipe.
   - **What did not work:** a second navigation view inside the split
     view's content (Pensum 0.1.0: no back swipe on the phone, owner
     2026-11-05), and moving the sidebar widget by hand between the
     navigation view's first page and an `AdwOverlaySplitView` (Pensum
     until 2026-11-06: the swipe back to the lists was missing on the
     phone, owner).
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
     early snaps back. Screenshots can't show gestures, and Broadway
     passes no touch events to GTK. Real touch works in a headless
     Mutter (`mutter --headless --wayland --virtual-monitor 360x720`
     with PipeWire) through its remote-desktop D-Bus API
     (`NotifyTouchDown`/`Motion`/`Up`); the seat offers touch only from
     the first touch on, so tap once before the swipe (Pensum, 2026-11-06).
10. **Thumb reach: frequent actions at the bottom.** On a phone held in
    one hand the thumb reaches the lower part of the screen easily and
    the top corners hardly at all[^hoober]; the HIG asks to start from
    the most constrained device and lets breakpoints move controls into
    a toolbar shown only at narrow widths.[^hig-adaptive]
    - Put the actions used most on a page (add, compose, search, start
      or stop, mark done, play controls) in a bottom bar of its
      `AdwToolbarView` (`add_bottom_bar`, a `GtkActionBar` or an
      `AdwClamp` with a box). Text fields that create something (add a
      task, write a message) go there too: they sit right above the
      on-screen keyboard.
    - The header bar keeps the title, the back button and the main or
      page menu, and few other controls.[^hig-header-bars] Rarely used
      and destructive actions (delete, archive) belong in menus or at
      the end of the page, not within easy reach.
    - View switchers move to the bottom (`AdwViewSwitcherBar`) when the
      window is narrow; 3–5 views.[^hig-view-switchers]
    - At most about four targets in a bottom bar at 360 px; the same
      bar may stay on the desktop.
    - A menu button in a bottom bar opens upwards
      (`direction = GTK_ARROW_TYPE_UP`).
    - Buttons in bottom bars: normal buttons, at least 44 px high
      (`min-height` in the app's CSS); not `pill`, which crashed the
      screenshot server ([screenshot testing](screenshot-testing.md)).
11. **Touch targets and gestures.**
    - Targets at least 44 × 44 px (WCAG 2.5.5[^wcag-target]; Apple
      44 pt, Material 48 dp): whole rows activatable, standalone icon
      buttons not smaller than libadwaita's default button, about 6 px
      between neighbouring targets.
    - Hover never reveals actions or essential information; every
      context-menu or long-press action is also reachable another way
      (a visible button, a menu, a keyboard shortcut).[^hig-pointer-touch]
    - Apps may use one- and two-finger gestures and drags from the left
      and right edges; three- and four-finger gestures and drags from
      the top and bottom edges belong to the system.[^hig-pointer-touch]
    - Don't focus a text field on start or when a page opens unless
      typing is the page's only purpose (a search page): on the phone it
      opens the on-screen keyboard over the content.
12. **Verify** every UI change with `scripts/screenshot.sh` at 360×720 and
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
[^hig-adaptive]: GNOME HIG – Scaling & adaptiveness
[^hig-pointer-touch]: GNOME HIG – Pointer and touch input
[^hig-header-bars]: GNOME HIG – Header bars
[^hig-view-switchers]: GNOME HIG – View switchers
[^hoober]: Steven Hoober, Design for Fingers and Thumbs Instead of Touch
[^wcag-target]: WCAG 2.2 – 2.5.5 Target Size (Enhanced)
[^as-relations]: AppStream relations (requires, recommends, supports)
