"""scripts/precheck.sh: metainfo and desktop files are validated, the
Mobile form factor is required, other files are skipped."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "precheck.sh"
DESKTOP = ROOT / "examples" / "de.nexumia.PhoshDemo.desktop"
METAINFO = ROOT / "examples" / "de.nexumia.PhoshDemo.metainfo.xml"

pytestmark = pytest.mark.skipif(
    not (shutil.which("appstreamcli") and shutil.which("desktop-file-validate")),
    reason="needs appstreamcli and desktop-file-validate")


def run(*files, cwd=ROOT):
    return subprocess.run([SCRIPT, *map(str, files)], cwd=cwd,
                          capture_output=True, text=True)


def test_the_demo_metadata_passes():
    result = run(DESKTOP, METAINFO, ROOT / "examples" / "adw-demo.py")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "desktop file:" in result.stdout and "metainfo:" in result.stdout


def test_desktop_file_without_mobile_fails(tmp_path):
    text = DESKTOP.read_text()
    assert "Mobile;" in text
    for value in ("Workstation;", "Workstation;Mobile"):   # also no trailing ;
        bad = tmp_path / "de.nexumia.PhoshDemo.desktop"
        bad.write_text("\n".join(
            f"X-Purism-FormFactor={value}" if line.startswith("X-Purism-FormFactor")
            else line for line in text.splitlines()) + "\n")
        result = run(bad)
        assert result.returncode == 1
        assert "X-Purism-FormFactor" in result.stdout


def test_invalid_desktop_file_fails(tmp_path):
    bad = tmp_path / "x.desktop"
    bad.write_text("[Desktop Entry]\nType=Application\n"
                   "X-Purism-FormFactor=Workstation;Mobile;\n")   # no Name, Exec
    result = run(bad)
    assert result.returncode == 1 and "desktop-file-validate failed" in result.stdout


def test_metainfo_without_id_fails(tmp_path):
    bad = tmp_path / "x.metainfo.xml"
    bad.write_text('<?xml version="1.0"?>\n<component type="desktop-application">'
                   "<name>X</name></component>\n")
    result = run(bad)
    assert result.returncode == 1 and "appstreamcli validate failed" in result.stdout


def test_templates_and_no_files_pass(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.desktop.in.in").write_text("@broken@")
    result = run(cwd=tmp_path)          # default data/*
    assert result.returncode == 0 and "nothing to check" in result.stdout
