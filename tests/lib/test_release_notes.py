"""Release notes for "What's New" from a metainfo file."""
from pathlib import Path

import gi
import pytest

gi.require_version("Adw", "1")
from gi.repository import Adw, GLib  # noqa: E402

from phosh_toolkit import release_notes  # noqa: E402

TWO = """<component><releases>
  <release version="0.2.0~dev.1" type="development"><description>
    <ul><li>Radar &amp; more.</li></ul>
  </description></release>
  <release version="0.1.0"><description><p>Old.</p></description></release>
</releases></component>"""


def write(directory, text, name="m.xml"):
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_newest_release(tmp_path):
    assert release_notes.newest(write(tmp_path, TWO)) == (
        "0.2.0~dev.1", "<ul><li>Radar &amp; more.</li></ul>")


@pytest.mark.parametrize("text", [
    None, "<component/>", "not xml",
    "<component><releases><release version='1'/></releases></component>",
    "<component><releases><release version='1'><description>  </description>"
    "</release></releases></component>",
])
def test_no_notes(tmp_path, text):
    path = None if text is None else write(tmp_path, text)
    assert release_notes.newest(path) is None


def test_missing_file_gives_no_notes(tmp_path):
    assert release_notes.newest(tmp_path / "missing.xml") is None


def test_find_prefers_the_installed_file(tmp_path, monkeypatch):
    installed = write(tmp_path / "share" / "metainfo", TWO,
                      "de.nexumia.App.metainfo.xml")
    source = write(tmp_path, TWO, "source.xml")
    monkeypatch.setattr(GLib, "get_system_data_dirs",
                        lambda: [str(tmp_path / "other"), str(tmp_path / "share")])
    assert release_notes.find("de.nexumia.App", source) == installed
    # The nightly app has its own id and file.
    assert release_notes.find("de.nexumia.App.Devel", source) == source
    assert release_notes.find("de.nexumia.App.Devel") is None
    assert release_notes.find("de.nexumia.App.Devel", tmp_path / "gone.xml") is None


def test_add_to_fills_the_about_dialog(tmp_path, monkeypatch):
    if not hasattr(Adw, "AboutDialog"):
        pytest.skip("libadwaita older than 1.5")
    Adw.init()
    monkeypatch.setattr(GLib, "get_system_data_dirs", lambda: [])
    dialog = Adw.AboutDialog()
    assert release_notes.add_to(dialog, "de.nexumia.App", write(tmp_path, TWO))
    assert dialog.get_release_notes_version() == "0.2.0~dev.1"
    assert dialog.get_release_notes() == "<ul><li>Radar &amp; more.</li></ul>"
    empty = Adw.AboutDialog()
    assert not release_notes.add_to(empty, "de.nexumia.App")
    assert empty.get_release_notes() == ""
