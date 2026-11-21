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
   The app talks to it through `broadway_dedup.py`
   ([shared render nodes](#shared-render-nodes-gtk-420-broadway_deduppy)).
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

# Shared render nodes (GTK 4.20+): `broadway_dedup.py`

The app does not connect to `gtk4-broadwayd` itself but to
`scripts/broadway_dedup.py`, a socket proxy the script starts on display
number + 100. Without it, apps on GTK 4.20 and later (GNOME 51 runtime:
GTK 4.24) make the display server abort or draw wrong pictures (#48).

- **Cause.** The Broadway renderer (`gsk/broadway/gskbroadwayrenderer.c`,
  `add_new_node`) gives every render node an id and sends "reuse id" for
  a node object it sent in the previous frame. GTK 4.20+ draws symbolic
  icons with `GtkSvg`, which caches its render node
  (`gtk/svg/gtksvgrenderer.c`, `can_reuse_node`), and the icon theme
  hands the same paintable to every widget that shows the icon. So one
  node object is in the tree several times (seen in Pensum's tree with
  `gsk_render_node_serialize()`: `opacity "node1" { … }` and later
  `child: "node1";`), and from the second frame on the same id is reused
  several times in one frame. `gtk4-broadwayd` takes a reused node with
  everything below it exactly once per frame
  (`gdk/broadway/broadway-output.c`, `append_node_ops`), so it aborts:

  ```
  Gdk:ERROR:../../../gdk/broadway/broadway-output.c:458:append_node_ops: assertion failed: (!reused_node->consumed)
  ```

  The code is the same in GTK 4.14.5 (Ubuntu 24.04) and GTK `main`, so a
  newer `gtk4-broadwayd` does not help. The abort seen with Cirro
  (`decode_nodes: assertion failed: (node != NULL)`) and icons missing
  in rows that repeat an icon have the same cause.
- **When.** Only when a frame reuses the shared node and the part of the
  tree around it changed, so it looks random: Pensum from the GNOME 51
  runtime against Ubuntu's broadwayd failed in 8 of 26 runs at 1000×700
  and 1 of 16 at 360×720 (2026-11-21), in CI in all three attempts of
  `task-desktop-light`. Apps on the host's GTK 4.14 do not share nodes
  (0 of 28 runs failed).
- **Fix in the script.** The proxy forwards everything, but in each
  frame (`SET_NODES` request) it replaces the second and later reuse of
  an id, and a reuse of a node below an already reused one, by a copy of
  that node with new ids (from 2³¹ on; the renderer's own ids stay
  below). A copy may show a texture the app released after its frame
  (textures drawn for unsupported nodes), which made the web client
  throw `Cannot read properties of undefined (reading 'ref')` and stop
  drawing; so the proxy holds a `RELEASE_TEXTURE` back while a node it
  could still copy uses the texture. With the proxy: 0 of 57 runs failed
  (31 at 1000×700) while it replaced reuses in 33 of 40 counted runs,
  no page errors, and each of the four shots was identical byte for
  byte in 10 runs (before, icons were missing in some). On a request it cannot read it says so and
  forwards unchanged from then on. Tests: `tests/test_broadway_dedup.py`.
- **Not fixed in GTK.** The bug is GTK's (renderer or daemon); no GTK
  issue was found for it (searched 2026-10-27). Real devices use Wayland
  and are not affected.
- **When a screenshot fails** the script prints the app's log, how
  `gtk4-broadwayd` ended (exit status and signal), its log and the
  proxy's log, so the reason is in the CI log.

`scripts/release.py` still takes a failed screenshot again, up to
`SHOT_ATTEMPTS` (3) times (`run_shot`); each attempt is a new run of the
script with its own display server, proxy and work directory. It was
added on 2026-11-20 against these aborts, before their cause was known.

# Known limits: pill buttons and reveal animations (GNOME 51)

Found with Pensum on 2026-11-05, reproduced locally with the app's
Flatpak on `org.gnome.Platform//51` and the toolkit's script:

- **broadwayd aborts** after `Gdk-WARNING: Duplicate call to
  gdk_frame_timings_submitted() with different values`; the script then
  reports "Unable to read from broadway server: eof".
- **Triggers**, each found by switching one change off at a time:
  two `pill` buttons in an `AdwToolbarView` bottom bar (3 of 6 runs
  failed; 6 of 6 passed without the `pill` class), and hiding a
  `GtkActionBar` with its reveal animation while a navigation page
  slides in (2 of 2 failed).
- **Workaround.** In bottom bars use normal buttons with a CSS
  `min-height: 44px` (thumb reach, [adaptive UI](adaptive-libadwaita.md)
  rule 11) instead of `pill`, and hide bars that change with the page
  with `set_visible` instead of `set_revealed`. Pensum's task shot then
  passed 6 of 6. Real devices use Wayland and are not known to be
  affected.
- **Width warnings first.** `Adwaita-WARNING: … exceeds … width:
  requested 370 px, 360 px available` repeats on every frame when a
  page is too wide for 360 px and also ended in a broadwayd crash; host
  libadwaita 1.5 does not print it, the GNOME 51 runtime does. Let
  labels in bars ellipsize.

# Requirements

`gtk4-broadwayd` (Ubuntu package `libgtk-4-bin`, installed by `setup.sh`),
`python3` 3.9 or later (standard library only, for `broadway_dedup.py`)
and Node with the `playwright` package and a Chromium it can launch.
Playwright is resolved from the current directory (a local
`node_modules`), then `NODE_PATH`, then the global npm root. CI installs
the version pinned in `scripts/package.json` with
`npm install --prefix scripts` and sets
`NODE_PATH=scripts/node_modules`; Dependabot proposes updates. The resolved path
is passed to the helper script, which runs from a temp directory. In
environments with a preinstalled Playwright Chromium, do not run
`playwright install`.
