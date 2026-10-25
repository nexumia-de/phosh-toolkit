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
#   -o FILE    output PNG (default: screenshot.png)
#   -W PX      viewport width  (default: 360)
#   -H PX      viewport height (default: 720)
#   -d SEC     seconds to wait after the window appeared (default: 2)
#   -s SCALE   device scale factor (default: 1)
#   -c SCHEME  colour scheme: light or dark (default: the app's default)
#   -e VAR=VAL environment variable for the app (repeatable)
#   -a ACTION  activate an application action once the window is shown,
#              e.g. app.about or app.step-time(12) (parameter as GVariant
#              text in brackets; repeatable). GTK exports only app.* actions
#              on D-Bus, not win.*.
#   -i APP_ID  application id for -a (default: taken from "flatpak run")
#   -F PATH    expose PATH read-only to a Flatpak app (repeatable)
#   -l FILE    also write the app's stdout/stderr to FILE
#   -n         do not maximize the window
#
# A command "flatpak run [options] <app id> ..." runs the installed Flatpak;
# the script adds the sandbox options Broadway needs.
#
# Example:
#   scripts/screenshot.sh -o shot.png -- python3 examples/adw-demo.py
#   scripts/screenshot.sh -c dark -a app.about -o about.png -- flatpak run de.nexumia.MyApp
#
# Requirements: gtk4-broadwayd (Ubuntu: libgtk-4-bin), dbus-daemon and gdbus,
# and Node with the "playwright" package and a Chromium it can launch.
set -euo pipefail

out=screenshot.png
width=360
height=720
delay=2
scale=1
scheme=
envs=()
actions=()
app_id=
expose=()
applog=
maximize=1

usage() { sed -n '2,35p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while getopts "o:W:H:d:s:c:e:a:i:F:l:nh" opt; do
  case $opt in
    o) out=$OPTARG ;;
    W) width=$OPTARG ;;
    H) height=$OPTARG ;;
    d) delay=$OPTARG ;;
    s) scale=$OPTARG ;;
    c) scheme=$OPTARG ;;
    e) envs+=("$OPTARG") ;;
    a) actions+=("$OPTARG") ;;
    i) app_id=$OPTARG ;;
    F) expose+=("$OPTARG") ;;
    l) applog=$OPTARG ;;
    n) maximize=0 ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done
shift $((OPTIND - 1))
[[ ${1:-} == "--" ]] && shift
(($#)) || usage 1

case $scheme in
  '') ;;
  # libadwaita's override; without a settings portal the default is light.
  light) envs+=(ADW_DEBUG_COLOR_SCHEME=prefer-light) ;;
  dark) envs+=(ADW_DEBUG_COLOR_SCHEME=prefer-dark) ;;
  *) echo "-c takes light or dark" >&2; exit 1 ;;
esac

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

# "flatpak run": the app id is the first argument after "run" that is not
# an option.
flatpak=0
if [[ $1 == flatpak && ${2:-} == run ]]; then
  flatpak=1
  if [[ -z $app_id ]]; then
    for arg in "${@:3}"; do
      [[ $arg == -* ]] || { app_id=$arg; break; }
    done
  fi
fi
if ((${#actions[@]})) && [[ -z $app_id ]]; then
  echo "-a needs the application id (-i)" >&2; exit 1
fi

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
bus_pid=
cleanup() {
  for pid in "${pids[@]}"; do kill "$pid" 2>/dev/null || true; done
  [[ -n $bus_pid ]] && kill "$bus_pid" 2>/dev/null
  wait 2>/dev/null || true
  rm -rf "$workdir"
}
trap cleanup EXIT

# gtk4-broadwayd listens on $XDG_RUNTIME_DIR/broadway<N+1>.socket. flatpak
# mounts /run/user/<uid> as the sandbox's runtime directory, so a Flatpak
# app only finds the socket there.
if [[ -z ${XDG_RUNTIME_DIR:-} || ! -d $XDG_RUNTIME_DIR ]]; then
  if [[ -d /run/user/$UID && -w /run/user/$UID ]]; then
    export XDG_RUNTIME_DIR=/run/user/$UID
  elif ((flatpak)); then
    echo "Flatpak apps need XDG_RUNTIME_DIR (/run/user/$UID)" >&2; exit 1
  else
    export XDG_RUNTIME_DIR="$workdir/run"
    install -d -m 700 "$XDG_RUNTIME_DIR"
  fi
fi

# One session bus for the app and for activating its actions.
if [[ -z ${DBUS_SESSION_BUS_ADDRESS:-} ]]; then
  command -v dbus-daemon >/dev/null || { echo "dbus-daemon not found" >&2; exit 1; }
  { read -r DBUS_SESSION_BUS_ADDRESS; read -r bus_pid; } < <(
    dbus-daemon --session --fork --nopidfile --print-address=1 --print-pid=1 2>/dev/null)
  export DBUS_SESSION_BUS_ADDRESS
fi

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
const [playwright, url, out, width, height, scale, delay, maximize, dir] = process.argv.slice(2);
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
  fs.writeFileSync(`${dir}/ready`, '');

  let win = null;
  for (const deadline = Date.now() + 30000; !win && Date.now() < deadline;) {
    await page.waitForTimeout(250);
    win = await page.evaluate(findWindow);
  }
  if (!win) throw new Error('no window appeared within 30 s');
  await page.waitForTimeout(500);
  win = await page.evaluate(findWindow);

  // Phosh maximizes every window. Broadway has no window manager, so
  // double-click the header bar (GTK's default: toggle maximize). Click the
  // centre of its visible part (a window with a default width larger than
  // the viewport extends past the right edge), 4 px below its top edge,
  // above any header bar button.
  const filled = win.x <= 0 && win.y <= 0 && win.width >= +width && win.height >= +height;
  if (maximize === '1' && !filled) {
    const left = Math.max(win.x, 0);
    const right = Math.min(win.x + win.width, +width);
    await page.mouse.dblclick((left + right) / 2, win.y + 4);
    // Move the pointer off the header bar, so no tooltip shows.
    await page.mouse.move(+width - 1, +height - 1);
  }
  // The shell activates the requested actions now, then writes "go".
  await page.waitForTimeout(500);
  fs.writeFileSync(`${dir}/shown`, '');
  for (const deadline = Date.now() + 30000; !fs.existsSync(`${dir}/go`);) {
    if (Date.now() > deadline) throw new Error('actions did not finish within 30 s');
    await page.waitForTimeout(100);
  }
  await page.waitForTimeout(+delay * 1000);
  await page.screenshot({ path: out });
  await browser.close();
})().catch((e) => { console.error(e.message || e); process.exit(1); });
EOF

# Chromium stays off the app's bus: it aborts when the bus goes away first.
env -u DBUS_SESSION_BUS_ADDRESS node "$workdir/shot.js" "$playwright" "http://127.0.0.1:$port/" "$(realpath -m "$out")" \
  "$width" "$height" "$scale" "$delay" "$maximize" "$workdir" &
shot_pid=$!
pids+=("$shot_pid")

for _ in $(seq 300); do [[ -e $workdir/ready ]] && break; sleep 0.1; done

envs=(GDK_BACKEND=broadway "BROADWAY_DISPLAY=:$display" GSETTINGS_BACKEND=memory "${envs[@]}")
if ((flatpak)); then
  # Inside the sandbox the variables are set with --env; XDG_CONFIG_DIRS
  # keeps the runtime's own directories after the dpi settings.
  sandbox=("--filesystem=xdg-run/broadway$((display + 1)).socket"
           "--filesystem=$workdir/xdg:ro"
           "--env=XDG_CONFIG_DIRS=$workdir/xdg:/app/etc/xdg:/etc/xdg")
  for var in "${envs[@]}"; do sandbox+=("--env=$var"); done
  for path in "${expose[@]}"; do sandbox+=("--filesystem=$(realpath "$path"):ro"); done
  command=(flatpak run "${sandbox[@]}" "${@:3}")
else
  command=(env "${envs[@]}" XDG_CONFIG_DIRS="$workdir/xdg:${XDG_CONFIG_DIRS:-/etc/xdg}" "$@")
fi
"${command[@]}" >"$workdir/app.log" 2>&1 &
app_pid=$!
pids+=("$app_pid")

fail() {
  echo "$1" >&2
  [[ -n $applog ]] && cp "$workdir/app.log" "$applog"
  echo "App log:" >&2
  cat "$workdir/app.log" >&2
  rm -f "$out"
  exit 1
}

# Activate the actions over the session bus (org.gtk.Actions on the
# application object), the way "gapplication action" does.
while [[ ! -e $workdir/shown ]]; do
  kill -0 "$shot_pid" 2>/dev/null || break
  kill -0 "$app_pid" 2>/dev/null || fail "App exited before its window was shown."
  sleep 0.1
done
if [[ -e $workdir/shown ]]; then
  object=/${app_id//./\/}
  object=${object//-/_}
  for action in "${actions[@]}"; do
    name=${action%%(*}
    param=[]
    [[ $action == *\(*\) ]] && { param=${action#*\(}; param="[<${param%\)}>]"; }
    [[ $name == app.* ]] || fail "Action $action: only app.* actions can be activated."
    gdbus call --session --dest "$app_id" --object-path "$object" \
      --method org.gtk.Actions.Activate "${name#*.}" "$param" '{}' >/dev/null ||
      fail "Could not activate $action."
  done
  : >"$workdir/go"
fi

shot_ok=1
wait "$shot_pid" || shot_ok=0
[[ -n $applog ]] && cp "$workdir/app.log" "$applog"
if ((shot_ok)) && kill -0 "$app_pid" 2>/dev/null; then
  echo "Saved $out (${width}x${height})"
else
  ((shot_ok)) && echo "App exited before the screenshot was taken." >&2
  fail "Screenshot failed."
fi
