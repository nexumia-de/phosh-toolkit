#!/usr/bin/env bash
# Phosh toolkit host setup for Ubuntu 24.04.
#
# Installs the GTK4/libadwaita development stack, Flatpak tooling and the
# Flathub remote. Idempotent: safe to run on every environment start, on a
# plain VM, or on a laptop.
#
# Usage:
#   ./setup.sh            # install everything
#   SKIP_FLATHUB=1 ./setup.sh   # skip adding the Flathub remote
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

PACKAGES=(
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
  weston
)

missing=()
for pkg in "${PACKAGES[@]}"; do
  if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q 'install ok installed'; then
    missing+=("$pkg")
  fi
done

if ((${#missing[@]})); then
  log "Installing ${#missing[@]} missing package(s): ${missing[*]}"
  export DEBIAN_FRONTEND=noninteractive
  "${SUDO[@]}" apt-get update -q
  "${SUDO[@]}" apt-get install -y -q --no-install-recommends "${missing[@]}"
else
  log "All apt packages already installed."
fi

if [[ -z "${SKIP_FLATHUB:-}" ]]; then
  if flatpak remotes --system --columns=name 2>/dev/null | grep -qx flathub; then
    log "Flathub remote already configured."
  else
    log "Adding Flathub remote (system-wide)."
    "${SUDO[@]}" flatpak remote-add --system --if-not-exists flathub \
      https://dl.flathub.org/repo/flathub.flatpakrepo
  fi
fi

if command -v node >/dev/null 2>&1 && node -e "require('playwright')" >/dev/null 2>&1; then
  log "Playwright (Node) found; scripts/screenshot.sh is ready."
else
  warn "Node Playwright not found. scripts/screenshot.sh needs it:"
  warn "  npm install -g playwright && npx playwright install chromium"
fi

log "Done."
