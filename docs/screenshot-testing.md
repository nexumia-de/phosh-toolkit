---
type: Tool
title: Screenshot testing
description: How scripts/screenshot.sh renders a GTK4 app (from the source tree or as an installed Flatpak) at phone size with Broadway and Playwright, opens states through app actions, switches light/dark, and the quirks it works around.
resource: ../scripts/screenshot.sh
tags: [testing, screenshot, broadway, playwright]
generated: { by: claude-code/2.1.310, at: 2026-10-25T19:00:00Z }
---

# Usage

```sh
scripts/screenshot.sh -o shot.png -- <command that starts the app>
scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- <command>   # desktop size
```

Options: `-o` output file, `-W`/`-H` viewport (default 360×720), `-d`
settle delay in seconds, `-s` device scale factor, `-c light|dark`
colour scheme, `-e VAR=VALUE` environment for the app, `-a ACTION`
activate an application action after the window appeared (repeatable,
e.g. `-a app.about`, `-a 'app.step-time(12)'`), `-i APP_ID` the app id
for `-a`, `-F PATH` expose a path read-only to a Flatpak app, `-l` save
the app log, `-n` do not maximize. The script exits non-zero and deletes
the output if the app crashes before the screenshot or an action fails.

An installed Flatpak is run as is; the script adds the sandbox options
Broadway needs after `run`, and takes the app id from the command:

```sh
scripts/screenshot.sh -c dark -a app.about -o about.png -- flatpak run de.nexumia.MyApp
```

The screenshots that ship with a release are declared in the app's
`release.toml` and taken by `scripts/release.py screenshots`, which calls
this script for every shot, size and colour scheme; see
[releases](releases.md).

For apps built with meson, run the built binary or `meson devenv`:

```sh
scripts/screenshot.sh -o shot.png -- meson devenv -C _build ./src/my-app
```

# How it works

1. Starts `gtk4-broadwayd` on a free display (port 8080 + display number).
2. Opens the Broadway page in headless Chromium via Node Playwright with
   the requested viewport. The browser viewport defines the Broadway
   screen size, so the browser connects **before** the app starts.
3. Starts a session bus with `dbus-daemon` if none exists, and the app
   with `GDK_BACKEND=broadway`, `GSETTINGS_BACKEND=memory`, and for `-c`
   `ADW_DEBUG_COLOR_SCHEME=prefer-light|prefer-dark` (libadwaita's
   override of the missing settings portal). For `flatpak run` the
   variables become `--env=` options, and the Broadway socket and the dpi
   settings directory (below) become `--filesystem=` options.
4. Waits for the window, maximizes it, moves the pointer away, activates
   the `-a` actions with `gdbus call … org.gtk.Actions.Activate` on the
   application object, waits `-d` seconds, takes the screenshot.

# Quirks worked around

- **DPI is unset under Broadway.** GTK reports `gtk-xft-dpi = -1`, which
  makes `sp` units (and therefore every `AdwBreakpoint` condition)
  evaluate wrongly: the breakpoint never applies. The script puts a
  `settings.ini` with `gtk-xft-dpi=98304` (96 dpi) first in
  `XDG_CONFIG_DIRS`.
- **No window manager.** Broadway places new windows at an offset and
  does not maximize them, while [Phosh](phosh.md) maximizes every window.
  The script double-clicks the header bar, which triggers GTK's default
  "toggle maximize" action. It clicks the centre of the header bar's
  visible part, because a window whose default width exceeds the
  viewport (e.g. 800 px at 360 px) extends past the right edge and its
  real centre is off screen, and only 4 px below the top edge, above
  any button: 23 px down the click hit Cirro's reload button and the
  window stayed unmaximized. Afterwards the pointer moves to the bottom
  right corner; left on the header bar it showed a button's tooltip in
  the picture.
- **Window actions are not on the bus.** GTK 4 exports the application's
  actions (`/de/nexumia/MyApp`, `org.gtk.Actions`) but no `/window/<id>`
  objects (checked with `gdbus introspect` on GNOME 51), so `-a` takes
  only `app.*` actions.
- **Flatpak runtime directory.** flatpak mounts `/run/user/<uid>` as the
  sandbox's runtime directory and the app looks for the Broadway socket
  there. Without `XDG_RUNTIME_DIR` the script uses `/run/user/<uid>` if
  it is writable and refuses Flatpak commands otherwise.
- **flatpak run needs a system bus** (`Could not connect: No such file
  or directory` without one). CI runners and desktops have one; in a bare
  container start it with `mkdir -p /run/dbus && dbus-daemon --system --fork`.
- **Chromium and the app's bus.** Chromium aborts when the session bus it
  joined goes away first, so it runs without `DBUS_SESSION_BUS_ADDRESS`.
- **Python interpreter mismatch.** `python3-gi` is built for the
  distribution's Python (3.12 on Ubuntu 24.04). If `python3` points to a
  different version (pyenv, update-alternatives), `import gi` fails with
  `cannot import name '_gi'`. `setup.sh` detects this and prints the
  matching interpreter. `examples/adw-demo.py` re-execs itself with the
  interpreter that matches `/usr/lib/python3/dist-packages/gi/_gi.cpython-3XX-*.so`,
  so `python3 examples/adw-demo.py` works both on a plain Ubuntu 24.04
  (python3 = 3.12) and on images where python3 is another version. For
  other PyGObject apps call the distribution interpreter explicitly, e.g.
  `/usr/bin/python3.12`.

# Known limits: shared render nodes (GTK 4.20+)

Found with Cirro on 2026-10-27, running the app from
`org.gnome.Platform//51` (GTK 4.24):

- **broadwayd aborts** with `Gdk:ERROR:…broadway-server.c:…:decode_nodes:
  assertion failed: (node != NULL)`. The app then fails with "Unable to
  read from broadway server" and the script with "App exited before its
  window was shown". In Cirro this happened after the double-click that
  maximizes the window, once the UI had more widgets (4 map pins, a
  sidebar list). It failed in 6 of 6 runs at 1000×700, both with
  Ubuntu's broadwayd (GTK 4.14) and with the runtime's own
  `gtk4-broadwayd`. So it is not a version mismatch between the two.
- **Repeated icons disappear.** In a list whose rows show the same
  symbolic icon (`view-more-symbolic` menu buttons), only one row's
  icon was drawn at 360×720. The widgets were mapped and allocated, so
  only the picture is wrong.
- **Likely cause.** The Broadway renderer
  (`gsk/broadway/gskbroadwayrenderer.c`) gives every render node an id
  and sends "reuse id" for a node it sent in the previous frame. GTK
  4.20+ draws symbolic icons with `GtkSvg`, whose renderer caches
  render nodes, so one node can appear in several places of a frame.
  Broadway's server and its web client keep one object per id, so the
  copies collide. This is not verified in the GTK sources; no GTK issue
  was found for it (searched 2026-10-27).
- **Workaround.** Start the window maximized in the app's demo mode
  (Cirro: `self.maximize()` when `CIRRO_DEMO_DATA` is set). The script
  then skips its double-click, and Cirro's 12 store shots passed 12 of
  12. Avoid store shots of lists with repeated icons until GTK fixes
  this. Real devices use Wayland and are not affected.

# Requirements

`gtk4-broadwayd` (Ubuntu package `libgtk-4-bin`, installed by `setup.sh`)
and Node with the `playwright` package and a Chromium it can launch.
Playwright is resolved from the current directory (a local
`node_modules`), then `NODE_PATH`, then the global npm root. CI installs
the version pinned in `scripts/package.json` with
`npm install --prefix scripts` and sets
`NODE_PATH=scripts/node_modules`; Dependabot proposes updates. The resolved path
is passed to the helper script, which runs from a temp directory. In
environments with a preinstalled Playwright Chromium, do not run
`playwright install`.
