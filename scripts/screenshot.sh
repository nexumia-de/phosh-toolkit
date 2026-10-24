#!/usr/bin/env bash
# Take a phone-sized screenshot of a GTK4 app.
#
# Starts gtk4-broadwayd, runs the app with the Broadway backend and captures
# the browser page with Playwright (Node, Chromium). The default size is the
# Phosh logical resolution 360x720. Like Phosh, the window is maximized.
#
# Usage:
#   scripts/screenshot.sh [options] -- <command> [args...]
#
# Options:
#   -o FILE   output PNG (default: screenshot.png)
#   -W PX     viewport width  (default: 360)
#   -H PX     viewport height (default: 720)
#   -d SEC    seconds to wait after the window appeared (default: 2)
#   -s SCALE  device scale factor (default: 1)
#   -l FILE   also write the app's stdout/stderr to FILE
#   -n        do not maximize the window
#
# Example:
#   scripts/screenshot.sh -o shot.png -- python3 examples/adw-demo.py
#
# Requirements: gtk4-broadwayd (Ubuntu: libgtk-4-bin) and Node with the
# "playwright" package and a Chromium it can launch.
set -euo pipefail

out=screenshot.png
width=360
height=720
delay=2
scale=1
applog=
maximize=1

usage() { sed -n '2,24p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while getopts "o:W:H:d:s:l:nh" opt; do
  case $opt in
    o) out=$OPTARG ;;
    W) width=$OPTARG ;;
    H) height=$OPTARG ;;
    d) delay=$OPTARG ;;
    s) scale=$OPTARG ;;
    l) applog=$OPTARG ;;
    n) maximize=0 ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done
shift $((OPTIND - 1))
[[ ${1:-} == "--" ]] && shift
(($#)) || usage 1

command -v gtk4-broadwayd >/dev/null || { echo "gtk4-broadwayd not found (install libgtk-4-bin)" >&2; exit 1; }
command -v node >/dev/null || { echo "node not found" >&2; exit 1; }

# Resolve playwright from the caller's directory (local node_modules),
# NODE_PATH or the global npm root. The helper script runs from a temp dir,
# so it gets the resolved path instead of resolving it itself.
resolve_playwright() { node -p "require.resolve('playwright')" 2>/dev/null; }
playwright=$(resolve_playwright) || playwright=
if [[ -z $playwright ]] && command -v npm >/dev/null; then
  NODE_PATH="$(npm root -g)${NODE_PATH:+:$NODE_PATH}"
  export NODE_PATH
  playwright=$(resolve_playwright) || playwright=
fi
[[ -n $playwright ]] || { echo "Node package 'playwright' not found" >&2; exit 1; }

# Pick a free Broadway display; display :N listens on port 8080+N.
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
display=
for n in $(seq 5 40); do
  if ! port_in_use $((8080 + n)); then display=$n; break; fi
done
[[ -n $display ]] || { echo "no free Broadway port in 8085-8120" >&2; exit 1; }
port=$((8080 + display))

workdir=$(mktemp -d)
pids=()
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  rm -rf "$workdir"
}
trap cleanup EXIT

# Broadway reports gtk-xft-dpi as unset (-1), which breaks "sp" units and
# therefore AdwBreakpoint conditions. Provide 96 dpi as a system default.
mkdir -p "$workdir/xdg/gtk-4.0"
printf '[Settings]\ngtk-xft-dpi=98304\n' >"$workdir/xdg/gtk-4.0/settings.ini"

gtk4-broadwayd --address 127.0.0.1 --port "$port" ":$display" >"$workdir/broadwayd.log" 2>&1 &
pids+=($!)
for _ in $(seq 50); do port_in_use "$port" && break; sleep 0.1; done
port_in_use "$port" || { cat "$workdir/broadwayd.log" >&2; echo "gtk4-broadwayd did not start" >&2; exit 1; }

cat >"$workdir/shot.js" <<'EOF'
const fs = require('fs');
const [playwright, url, out, width, height, scale, delay, maximize, readyFile] = process.argv.slice(2);
const { chromium } = require(playwright);

// Largest surface element = the window's content area (without CSD shadow).
const findWindow = () => {
  let best = null, area = 0;
  for (const top of document.body.children) {
    for (const el of top.querySelectorAll('div')) {
      const r = el.getBoundingClientRect();
      if (r.width * r.height > area) { area = r.width * r.height; best = r.toJSON(); }
    }
  }
  return best;
};

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: +width, height: +height },
    deviceScaleFactor: +scale,
  });
  // The browser defines the Broadway screen size, so connect before the
  // app starts, then tell the shell to launch it.
  await page.goto(url);
  await page.waitForTimeout(500);
  fs.writeFileSync(readyFile, '');

  let win = null;
  for (const deadline = Date.now() + 30000; !win && Date.now() < deadline;) {
    await page.waitForTimeout(250);
    win = await page.evaluate(findWindow);
  }
  if (!win) throw new Error('no window appeared within 30 s');
  await page.waitForTimeout(500);
  win = await page.evaluate(findWindow);

  // Phosh maximizes every window. Broadway has no window manager, so
  // double-click the header bar (GTK's default: toggle maximize).
  const filled = win.x <= 0 && win.y <= 0 && win.width >= +width && win.height >= +height;
  if (maximize === '1' && !filled) {
    await page.mouse.dblclick(win.x + win.width / 2, win.y + 23);
  }
  await page.waitForTimeout(+delay * 1000);
  await page.screenshot({ path: out });
  await browser.close();
})().catch((e) => { console.error(e.message || e); process.exit(1); });
EOF

ready="$workdir/ready"
node "$workdir/shot.js" "$playwright" "http://127.0.0.1:$port/" "$(realpath -m "$out")" \
  "$width" "$height" "$scale" "$delay" "$maximize" "$ready" &
shot_pid=$!

for _ in $(seq 300); do [[ -e $ready ]] && break; sleep 0.1; done

launcher=()
if command -v dbus-run-session >/dev/null && [[ -z ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
  launcher=(dbus-run-session --)
fi

GDK_BACKEND=broadway BROADWAY_DISPLAY=":$display" GSETTINGS_BACKEND=memory \
  XDG_CONFIG_DIRS="$workdir/xdg:${XDG_CONFIG_DIRS:-/etc/xdg}" \
  "${launcher[@]}" "$@" >"$workdir/app.log" 2>&1 &
app_pid=$!
pids+=("$app_pid")

shot_ok=1
wait "$shot_pid" || shot_ok=0
[[ -n $applog ]] && cp "$workdir/app.log" "$applog"
if ((shot_ok)) && kill -0 "$app_pid" 2>/dev/null; then
  echo "Saved $out (${width}x${height})"
else
  ((shot_ok)) && echo "App exited before the screenshot was taken." >&2
  echo "Screenshot failed. App log:" >&2
  cat "$workdir/app.log" >&2
  rm -f "$out"
  exit 1
fi
