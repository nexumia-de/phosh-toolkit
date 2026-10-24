---
type: Tool
title: Screenshot testing
description: How scripts/screenshot.sh renders a GTK4 app at phone size with Broadway and Playwright, and the quirks it works around.
resource: ../scripts/screenshot.sh
tags: [testing, screenshot, broadway, playwright]
generated: { by: claude-code/2.1.310, at: 2026-10-24T20:05:00Z }
---

# Usage

```sh
scripts/screenshot.sh -o shot.png -- <command that starts the app>
scripts/screenshot.sh -W 1000 -H 700 -o wide.png -- <command>   # desktop size
```

Options: `-o` output file, `-W`/`-H` viewport (default 360×720), `-d`
settle delay in seconds, `-s` device scale factor, `-l` save the app log,
`-n` do not maximize. The script exits non-zero and deletes the output if
the app crashes before the screenshot.

For apps built with meson, run the built binary or `meson devenv`:

```sh
scripts/screenshot.sh -o shot.png -- meson devenv -C _build ./src/my-app
```

# How it works

1. Starts `gtk4-broadwayd` on a free display (port 8080 + display number).
2. Opens the Broadway page in headless Chromium via Node Playwright with
   the requested viewport. The browser viewport defines the Broadway
   screen size, so the browser connects **before** the app starts.
3. Starts the app with `GDK_BACKEND=broadway`, `GSETTINGS_BACKEND=memory`
   and, if no session bus exists, inside `dbus-run-session`.
4. Waits for the window, maximizes it, waits `-d` seconds, takes the
   screenshot.

# Quirks worked around

- **DPI is unset under Broadway.** GTK reports `gtk-xft-dpi = -1`, which
  makes `sp` units (and therefore every `AdwBreakpoint` condition)
  evaluate wrongly: the breakpoint never applies. The script puts a
  `settings.ini` with `gtk-xft-dpi=98304` (96 dpi) first in
  `XDG_CONFIG_DIRS`.
- **No window manager.** Broadway places new windows at an offset and
  does not maximize them, while [Phosh](phosh.md) maximizes every window.
  The script double-clicks the center of the header bar, which triggers
  GTK's default "toggle maximize" action. Apps whose header bar center is
  an interactive widget (e.g. a search entry) may need `-n` and a window
  default size of 360×720 instead.
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

# Requirements

`gtk4-broadwayd` (Ubuntu package `libgtk-4-bin`, installed by `setup.sh`)
and Node with the `playwright` package and a Chromium it can launch. In
environments with a preinstalled Playwright Chromium, do not run
`playwright install`.
