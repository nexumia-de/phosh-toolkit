---
type: Guideline
title: Visual design
description: How Phosh apps look: stock libadwaita styling, typography, colour, icons, text and feedback patterns, following the GNOME HIG.
tags: [ui, design, libadwaita, hig, guideline]
generated: { by: claude-code/2.1.310, at: 2026-10-25T12:00:00Z }
sources:
  - id: hig-styling
    resource: https://developer.gnome.org/hig/guidelines/ui-styling.html
    title: GNOME HIG – UI styling
  - id: hig-writing
    resource: https://developer.gnome.org/hig/guidelines/writing-style.html
    title: GNOME HIG – Writing style
  - id: hig-typography
    resource: https://developer.gnome.org/hig/guidelines/typography.html
    title: GNOME HIG – Typography
  - id: hig-icons
    resource: https://developer.gnome.org/hig/guidelines/ui-icons.html
    title: GNOME HIG – UI icons
  - id: adw-classes
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/style-classes.html
    title: libadwaita style classes
  - id: adw-vars
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/css-variables.html
    title: libadwaita CSS variables
  - id: adw-styles
    resource: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/1-latest/styles-and-appearance.html
    title: libadwaita styles and appearance
  - id: adw-news
    resource: https://gitlab.gnome.org/GNOME/libadwaita/-/blob/main/NEWS
    title: libadwaita NEWS (1.6 CSS variables, 1.7 .dimmed)
  - id: adw-debug
    resource: https://gitlab.gnome.org/GNOME/libadwaita/-/blob/main/src/adw-settings.c
    title: libadwaita adw-settings.c (ADW_DEBUG_* environment variables)
---

# Goal

Every app looks like a well-made GNOME core app: stock Adwaita, no own
branding, no custom theme. Users get dark mode, high contrast and their
accent colour for free, and the apps look consistent with each other.
Layout and responsiveness are covered by
[adaptive libadwaita UI](adaptive-libadwaita.md); this page covers looks.

# Rules

1. **Stock widgets and style classes first, custom CSS last.** The HIG asks
   to keep custom styling to a minimum and to build on existing style
   classes and colour variables, which adapt to light, dark and
   high-contrast styles automatically.[^hig-styling] Before writing CSS,
   check the style class list.[^adw-classes] Most needs are covered:

   | Need | Use |
   |------|-----|
   | Main action of a view | `suggested-action` (with `pill` when standalone, e.g. in an `AdwStatusPage`) |
   | Dangerous action | `destructive-action`, confirmed in an `AdwAlertDialog` |
   | Settings, lists of items | `AdwPreferencesGroup` or `GtkListBox` with `boxed-list` |
   | Read-only key/value rows | `AdwActionRow` with `property` |
   | Grouped tile, clickable panel | `card` (on a `GtkButton` it gets hover/press states) |
   | Secondary text | `dimmed` (1.7+), never a hand-set opacity |
   | Numbers that change or align | `numeric` |
   | Buttons over a map or image | `osd` with `circular` or `pill` |
   | Status colour on a label/entry | `success`, `warning`, `error`, `accent` |

2. **Colours only through CSS variables.** When CSS is unavoidable, use
   `var(--accent-bg-color)`, `var(--window-bg-color)`, `var(--border-color)`
   etc.[^adw-vars] Never hard-code hex values or "blue" for UI chrome, and
   never use the GTK 3 named colours (`@theme_bg_color`, …), which do not
   pick up overrides.[^adw-vars] Do not override the accent colour: apps
   follow the system accent.[^adw-styles]
   **Exception: data colours.** Colours that encode data (radar scale,
   temperature map) are part of the content and may be fixed. They must
   stay legible on light and dark backgrounds, and colour must never be the
   only carrier of information: add labels, a legend or shapes.[^hig-styling]
3. **Typography only through style classes.** Use `title-1`…`title-4`,
   `heading`, `body`, `caption`, `caption-heading`, `monospace`,
   `numeric`.[^adw-classes] No hard-coded font families or sizes, no italics
   for emphasis, no all caps.[^hig-typography] Few levels per view: one
   title, headings, body, captions.
4. **Spacing on a 6 px grid.** libadwaita toolbars use 6 px margins and
   spacing.[^adw-classes] Use 6, 12, 18 or 24 px for `spacing` and margins,
   12 px as the default gap between groups. Let `AdwClamp`,
   `AdwPreferencesPage` and boxed lists do the padding instead of tuning
   margins per widget.
5. **Icons.** UI icons are `*-symbolic` names from the icon theme; reuse
   existing ones before drawing your own.[^hig-icons] A control has either
   an icon or a label, not both (exceptions: pill buttons and
   `AdwButtonContent`).[^hig-icons] Every icon-only button needs a
   `tooltip-text` (touch users never see it, so keep the icon obvious) and
   an accessible label for screen readers. The app
   icon follows the GNOME app icon style (full colour, `.svg`).
6. **Feedback patterns.**
   - Empty, error and offline views: `AdwStatusPage` with an icon, a short
     title and, where it helps, one `pill` button ("Retry").
   - Transient confirmations and non-fatal errors: `AdwToast` in an
     `AdwToastOverlay`, never custom message bars.
   - Persistent state the user should know about (offline, stale data):
     `AdwBanner`.
   - Loading: `AdwSpinner` (1.6+) or `AdwSpinnerPaintable` in an
     `AdwStatusPage`; no custom progress animations.
7. **Text.** Short and neutral, US English, no "e.g."/"i.e.".[^hig-writing]
   Header capitalisation for titles, header bars, buttons and menu items
   ("Find and Replace"); sentence capitalisation for descriptions, row
   subtitles, check boxes and entries.[^hig-writing] Use proper Unicode:
   `…` for ellipses, `–` for ranges, `×` for dimensions, `°C`, typographic
   quotes. Write units with a space ("12 mm/h").
8. **Dark and high contrast.** Follow the system style; offer a per-app
   style switch only if the app is used for long periods.[^hig-styling]
   Any custom drawing (maps, charts) reads colours from the style
   (`AdwStyleManager:dark`, `prefers-color-scheme: dark`,
   `prefers-contrast: more`) instead of assuming a light
   background.[^adw-styles]
9. **Where styles live.** If an app needs CSS, put it in one
   `style.css` resource loaded by `AdwApplication` (plus `style-dark.css` /
   `style-hc.css` if needed),[^adw-styles] not in Python strings scattered
   over widgets. Custom classes get an app prefix (`.cirro-swatch`).
10. **Layout files.** Prefer Blueprint or `.ui` files for anything bigger
    than a few widgets, so structure and logic stay apart and patterns can
    be copied between apps consistently.

# Version notes

| Feature | libadwaita |
|---------|------------|
| CSS variables (`var(--accent-color)` …) | 1.6[^adw-news] |
| `AdwSpinner`, `AdwBottomSheet` | 1.6 |
| `.dimmed` (replaces deprecated `.dim-label`) | 1.7[^adw-news] |
| `.document` | 1.8[^adw-classes] |

Flatpak builds use the GNOME runtime (51 in the current manifests), which
has all of these. Host builds and
[`scripts/screenshot.sh`](screenshot-testing.md) on Ubuntu 24.04 run
libadwaita 1.5 and GTK 4.14: `.dimmed` has no effect there and `var(--…)`
does not parse. Host screenshots can therefore look slightly off for
these features; judge them in a Flatpak build.

# Review checklist

Use this when reviewing a UI change, together with the 360×720 screenshot:

- [ ] No new CSS that a style class or widget already covers.
- [ ] No hard-coded colours or font sizes in UI chrome.
- [ ] Exactly one `suggested-action` per view at most.
- [ ] Every icon-only button has a tooltip and an accessible label.
- [ ] Empty/error/offline states use `AdwStatusPage`, `AdwToast` or `AdwBanner`.
- [ ] Capitalisation and Unicode as in rule 7.
- [ ] Looks right in dark style (`ADW_DEBUG_COLOR_SCHEME=prefer-dark`) and
      high contrast (`ADW_DEBUG_HIGH_CONTRAST=1`).[^adw-debug]

[^hig-styling]: GNOME HIG – UI styling
[^hig-writing]: GNOME HIG – Writing style
[^hig-typography]: GNOME HIG – Typography
[^hig-icons]: GNOME HIG – UI icons
[^adw-classes]: libadwaita style classes
[^adw-vars]: libadwaita CSS variables
[^adw-styles]: libadwaita styles and appearance
[^adw-news]: libadwaita NEWS (1.6 CSS variables, 1.7 .dimmed)
[^adw-debug]: libadwaita adw-settings.c (ADW_DEBUG_* environment variables)
