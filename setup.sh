#!/usr/bin/env bash
# Phosh toolkit host setup for Ubuntu 24.04.
#
# Installs the GTK4/libadwaita development stack, Flatpak tooling and the
# Flathub remote. Idempotent: safe to run on every environment start, on a
# plain VM, or on a laptop.
#
# Usage:
#   ./setup.sh                    # full development setup (default)
#   SETUP_PROFILE=ci ./setup.sh   # lean set for the validate CI job
#   SKIP_FLATHUB=1 ./setup.sh     # skip adding the Flathub remote
#
# Profiles:
#   full  Everything for app development: build tools, GTK4/libadwaita dev
#         packages, Blueprint, Vala, Rust, PyGObject, Flatpak tooling, cage.
#   ci    Only what validation needs: desktop-file-validate, appstreamcli,
#         the shell linter and the runtime for scripts/screenshot.sh
#         (Broadway, GTK4/libadwaita typelibs, PyGObject). No Flatpak.
set -euo pipefail

log() { printf '\033[1;34m[phosh-toolkit]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[phosh-toolkit] WARNING:\033[0m %s\n' "$*" >&2; }

if [[ $EUID -eq 0 ]]; then
  SUDO=()
elif command -v sudo >/dev/null 2>&1; then
  SUDO=(sudo)
else
  echo "This script needs root or sudo." >&2
  exit 1
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
    warn "Tested on Ubuntu 24.04 only; detected ${PRETTY_NAME:-unknown}. Continuing."
  fi
fi

profile=${SETUP_PROFILE:-full}

CI_PACKAGES=(
  desktop-file-utils
  appstream
  librsvg2-common       # SVG pixbuf loader, needed by appstreamcli compose
  libgtk-4-bin          # gtk4-broadwayd, used by scripts/screenshot.sh
  gir1.2-gtk-4.0
  gir1.2-adw-1
  python3-gi
  shellcheck
)

FULL_PACKAGES=(
  # Build tooling
  build-essential
  meson
  ninja-build
  pkg-config
  gettext
  git
  # Validation
  desktop-file-utils
  appstream
  shellcheck
  # GTK4 + libadwaita
  libgtk-4-dev
  libgtk-4-bin          # gtk4-broadwayd, used by scripts/screenshot.sh
  libadwaita-1-dev
  gir1.2-gtk-4.0
  gir1.2-adw-1
  blueprint-compiler
  # Languages
  valac
  rustc
  cargo
  python3-gi
  # Packaging and testing
  flatpak
  flatpak-builder
  librsvg2-common       # SVG pixbuf loader, needed by appstreamcli compose
  elfutils              # eu-strip, needed by flatpak-builder for compiled modules
  # Headless Wayland compositor for testing the Wayland backend. Not weston:
  # libweston pulls in FFmpeg, FreeRDP, GStreamer and flite via its
  # VNC/RDP/PipeWire backends (+112 packages, +72 MB; see
  # docs/host-setup.md).
  cage
)

case $profile in
  full) PACKAGES=("${FULL_PACKAGES[@]}") ;;
  ci) PACKAGES=("${CI_PACKAGES[@]}") ;;
  *) echo "Unknown SETUP_PROFILE '$profile' (expected: full, ci)." >&2; exit 1 ;;
esac
log "Profile: $profile"

missing=()
for pkg in "${PACKAGES[@]}"; do
  if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed'; then
    missing+=("$pkg")
  fi
done

if ((${#missing[@]})); then
  log "Installing ${#missing[@]} missing package(s): ${missing[*]}"
  # sudo resets the environment, so pass DEBIAN_FRONTEND through env. Wait
  # at most 120 s for a dpkg lock held by e.g. unattended-upgrades, and
  # retry downloads whose connection stalls for 30 s instead of hanging.
  apt=("${SUDO[@]}" env DEBIAN_FRONTEND=noninteractive apt-get
    -o DPkg::Lock::Timeout=120 -o Acquire::Retries=3 -o Acquire::http::Timeout=30)
  "${apt[@]}" update -q
  "${apt[@]}" install -y -q --no-install-recommends "${missing[@]}"
else
  log "All apt packages already installed."
fi

if [[ $profile == ci ]]; then
  log "Skipping Flathub remote (ci profile has no Flatpak)."
elif [[ -z "${SKIP_FLATHUB:-}" ]]; then
  if flatpak remotes --system --columns=name 2>/dev/null | grep -qx flathub; then
    log "Flathub remote already configured."
  else
    log "Adding Flathub remote (system-wide)."
    "${SUDO[@]}" flatpak remote-add --system --if-not-exists flathub \
      https://dl.flathub.org/repo/flathub.flatpakrepo
  fi
fi

# python3-gi is built for the distribution's Python (3.12 on Ubuntu 24.04).
# Some images point python3 at another version, where "import gi" fails.
gi_python=
for so in /usr/lib/python3/dist-packages/gi/_gi.cpython-3*-*.so; do
  [[ -e $so ]] || continue
  ver=${so##*/_gi.cpython-3}
  ver=${ver%%-*}
  [[ -x /usr/bin/python3.$ver ]] && gi_python=/usr/bin/python3.$ver && break
done
if python3 -c 'import gi' >/dev/null 2>&1; then
  log "PyGObject works with python3 ($(python3 -c 'import sys; print(sys.version.split()[0])'))."
elif [[ -n $gi_python ]] && "$gi_python" -c 'import gi' >/dev/null 2>&1; then
  warn "python3 is $(python3 --version 2>&1), but python3-gi is built for $gi_python."
  warn "Run PyGObject apps with $gi_python (the examples re-exec themselves)."
else
  warn "PyGObject (python3-gi) cannot be imported."
fi

if command -v node >/dev/null 2>&1 && node -e "require('playwright')" >/dev/null 2>&1; then
  log "Playwright (Node) found; scripts/screenshot.sh is ready."
else
  warn "Node Playwright not found. scripts/screenshot.sh needs it:"
  warn "  npm install -g playwright && npx playwright install chromium"
fi

log "Done."
