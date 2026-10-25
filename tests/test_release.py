import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import release  # noqa: E402

METAINFO = """\
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>de.nexumia.Test</id>
  <name>Test</name>
  <releases>
    <release version="0.1.0" date="2026-10-24">
      <description>
        <p>First release.</p>
      </description>
    </release>
  </releases>
</component>
"""


@pytest.fixture
def app(tmp_path):
    (tmp_path / "release.toml").write_text(
        'metainfo = "app.metainfo.xml"\n'
        'version-files = ["meson.build", "app.py"]\n')
    (tmp_path / "app.metainfo.xml").write_text(METAINFO)
    (tmp_path / "meson.build").write_text(
        "project('t', version: '0.1.0', meson_version: '>= 1.0')\n")
    (tmp_path / "app.py").write_text('VERSION = "0.1.0"\n')
    (tmp_path / "changelog.d").mkdir()
    (tmp_path / "changelog.d" / "README.md").write_text("Fragments.\n")
    return tmp_path


def fragment(app, name, text):
    (app / "changelog.d" / name).write_text(text)


def run(app, *args):
    return release.main(["--root", str(app), *args])


def test_fix_bumps_patch_and_feature_bumps_minor(app, capsys):
    fragment(app, "crash.fix.md", "Fixed a crash.\n")
    assert run(app, "next-version") == 0
    assert capsys.readouterr().out == "0.1.1\n"
    fragment(app, "map.feature.md", "A map.\n")
    assert run(app, "next-version") == 0
    assert capsys.readouterr().out == "0.2.0\n"


def test_prepare_bumps_files_adds_release_and_deletes_fragments(app, capsys):
    fragment(app, "zoom.fix.md", "Zooming no longer\njumps & flickers.\n")
    fragment(app, "radar.feature.md", "Animated radar.\n\nA time bar.\n")
    assert run(app, "prepare", "--date", "2026-11-01") == 0
    assert capsys.readouterr().out == "0.2.0\n"
    assert "version: '0.2.0'" in (app / "meson.build").read_text()
    assert 'VERSION = "0.2.0"' in (app / "app.py").read_text()
    text = (app / "app.metainfo.xml").read_text()
    root = ET.fromstring(text)
    first = root.find("releases/release")
    assert first.get("version") == "0.2.0" and first.get("date") == "2026-11-01"
    # Features first; lines of a paragraph joined; XML escaped.
    assert [li.text for li in first.iterfind("description/ul/li")] == [
        "Animated radar.", "A time bar.", "Zooming no longer jumps & flickers."]
    assert '    <release version="0.2.0" date="2026-11-01">\n' \
           '      <description>\n        <ul>\n' in text
    assert sorted(p.name for p in (app / "changelog.d").iterdir()) == ["README.md"]
    # Notes for the GitHub release.
    assert run(app, "notes", "0.2.0") == 0
    assert capsys.readouterr().out == (
        "- Animated radar.\n- A time bar.\n"
        "- Zooming no longer jumps & flickers.\n")


def test_prepare_without_fragments_does_nothing(app):
    assert run(app, "prepare") == 3
    assert (app / "app.metainfo.xml").read_text() == METAINFO


def test_prepare_rejects_older_version(app):
    fragment(app, "x.fix.md", "X.\n")
    assert run(app, "prepare", "--version", "0.1.0") == 1


def test_invalid_fragment_names_fail(app):
    fragment(app, "x.bugfix.md", "X.\n")
    assert run(app, "check") == 1


def test_check_requires_fragment_for_code_changes(app, tmp_path):
    changed = tmp_path / "changed.txt"
    changed.write_text("docs/log.md\ntests/test_x.py\nREADME.md\n")
    assert run(app, "check", "--changed", str(changed)) == 0
    changed.write_text("docs/log.md\napp.py\n")
    assert run(app, "check", "--changed", str(changed)) == 1
    fragment(app, "x.fix.md", "X.\n")
    changed.write_text("app.py\nchangelog.d/x.fix.md\n")
    assert run(app, "check", "--changed", str(changed)) == 0


def test_devel_release_for_nightly(app, capsys):
    fragment(app, "x.feature.md", "X.\n")
    assert run(app, "devel", "--suffix", "20261101.abc1234",
               "--date", "2026-11-01") == 0
    assert capsys.readouterr().out == "0.2.0~dev.20261101.abc1234\n"
    root = ET.parse(app / "app.metainfo.xml").getroot()
    first = root.find("releases/release")
    assert first.get("type") == "development"
    # The stable version is still the one releases compare against.
    assert run(app, "latest") == 0
    assert capsys.readouterr().out == "0.1.0\n"


def test_screenshots_listed_with_release_urls(app):
    with (app / "release.toml").open("a") as f:
        f.write('[[screenshots.shot]]\nname = "main"\ncaption = "Main window"\n'
                '[[screenshots.shot]]\nname = "about"\ncaption = "About"\n'
                'actions = ["app.about"]\n')
    fragment(app, "x.fix.md", "X.\n")
    assert run(app, "prepare", "--repo", "owner/app") == 0
    root = ET.parse(app / "app.metainfo.xml").getroot()
    shots = root.findall("screenshots/screenshot")
    base = "https://github.com/owner/app/releases/download/v0.1.1/"
    assert [s.findtext("image") for s in shots] == [
        base + "main-phone-light.png", base + "main-desktop-light.png",
        base + "about-phone-light.png", base + "about-desktop-light.png"]
    assert [s.get("type") for s in shots] == ["default", None, None, None]
    # A second release replaces the list instead of adding another.
    fragment(app, "y.fix.md", "Y.\n")
    assert run(app, "prepare", "--repo", "owner/app") == 0
    root = ET.parse(app / "app.metainfo.xml").getroot()
    assert len(root.findall("screenshots")) == 1
    assert "v0.1.2/" in root.find("screenshots/screenshot/image").text
    # The tag build checks that every listed file was taken.
    out = app / "out"
    out.mkdir()
    text = (app / "app.metainfo.xml").read_text()
    with pytest.raises(release.ReleaseError):
        release.check_listed(text, out)
    for name in ("main", "about"):
        for size in ("phone", "desktop"):
            (out / f"{name}-{size}-light.png").write_bytes(b"")
    release.check_listed(text, out)


def test_metainfo_still_validates(app):
    fragment(app, "x.feature.md", "X & Y.\n")
    assert run(app, "prepare") == 0
    result = subprocess.run(
        ["appstreamcli", "validate", "--no-net", "--format=text",
         str(app / "app.metainfo.xml")], capture_output=True, text=True)
    # The fixture lacks required fields; only check the release parts.
    assert "release" not in result.stdout.lower(), result.stdout


def test_flathub_manifest_builds_the_app_from_the_tag(tmp_path, capsys):
    import json
    manifest = {
        "id": "de.nexumia.Test",
        "modules": [
            {"name": "lib", "sources": [{"type": "archive", "url": "u"}]},
            {"name": "app", "buildsystem": "meson",
             "sources": [{"type": "dir", "path": ".", "skip": ["tests"]},
                         {"type": "file", "path": "extra.txt"}]},
        ],
    }
    path = tmp_path / "m.json"
    path.write_text(json.dumps(manifest))
    sha = "0123456789abcdef0123456789abcdef01234567"
    assert release.main(["flathub-manifest", str(path), "--url",
                         "https://github.com/o/app.git", "--tag", "v1.2.0",
                         "--commit", sha]) == 0
    result = json.loads(capsys.readouterr().out)
    # Third-party modules stay as they are.
    assert result["modules"][0] == manifest["modules"][0]
    git, extra = result["modules"][1]["sources"]
    assert git == {"type": "git", "url": "https://github.com/o/app.git",
                   "tag": "v1.2.0", "commit": sha,
                   "x-checker-data": {"type": "git",
                                      "tag-pattern": r"^v([\d.]+)$"}}
    assert extra == {"type": "file", "path": "extra.txt"}


def test_flathub_manifest_needs_a_full_commit(tmp_path):
    import json
    path = tmp_path / "m.json"
    path.write_text(json.dumps({"modules": [
        {"name": "app", "sources": [{"type": "dir", "path": "."}]}]}))
    assert release.main(["flathub-manifest", str(path), "--url", "u",
                         "--tag", "v1", "--commit", "abc1234"]) == 1
