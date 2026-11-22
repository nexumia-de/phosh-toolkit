#!/usr/bin/env bash
# Fast metadata checks, the ones a Flatpak build would only show after
# many minutes: every AppStream metainfo and desktop file among the
# given files is validated without network, and a desktop file must
# declare the Mobile form factor (Phosh hides the app otherwise,
# docs/phosh.md).
#
# Usage: precheck.sh [FILE...]        default: data/*
#
# Used by the Precheck job of the reusable Flatpak workflow and by the
# pre-commit hooks (.pre-commit-hooks.yaml). Templates (*.in) and other
# files are skipped. Exit status 1 if a check failed.
set -uo pipefail

if [[ $# -eq 0 ]]; then
  shopt -s nullglob
  set -- data/*
fi

failed=0
checked=0
fail() {
  # ::error is shown as an annotation by GitHub and reads fine elsewhere.
  echo "::error file=$1::$2"
  failed=1
}

for file in "$@"; do
  [[ -f $file ]] || continue
  case $file in
    *.metainfo.xml | *.appdata.xml)
      checked=$((checked + 1))
      echo "metainfo: $file"
      appstreamcli validate --no-net "$file" || fail "$file" "appstreamcli validate failed"
      ;;
    *.desktop)
      checked=$((checked + 1))
      echo "desktop file: $file"
      desktop-file-validate "$file" || fail "$file" "desktop-file-validate failed"
      grep -Eiq '^X-Purism-FormFactor=.*mobile;' "$file" ||
        fail "$file" "X-Purism-FormFactor needs 'Mobile;' with the trailing ';' (Phosh hides the app otherwise)"
      ;;
  esac
done

if [[ $checked -eq 0 ]]; then
  echo "precheck: no metainfo or desktop file among the given files; nothing to check."
fi
exit "$failed"
