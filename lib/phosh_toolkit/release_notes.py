"""Release notes from the installed AppStream metainfo, for "What's New"
in the About dialog: the same text GNOME Software shows. The release
workflow writes the <release> elements (docs/releases.md); this only
reads them. No GTK in newest(); add_to() takes an AdwAboutDialog."""
import xml.etree.ElementTree as ET
from pathlib import Path

from gi.repository import GLib


def find(app_id, source=None):
    """Path of the installed metainfo of `app_id` (the nightly app passes
    its own id, <app id>.Devel); else `source`, the file in the source
    tree for a run without installation; else None."""
    for directory in GLib.get_system_data_dirs():
        path = Path(directory) / "metainfo" / f"{app_id}.metainfo.xml"
        if path.is_file():
            return path
    if source is not None and Path(source).is_file():
        return Path(source)
    return None


def newest(path):
    """(version, description markup) of the newest release in the
    metainfo at `path`, or None. The markup is AppStream's (<p>, <ul>,
    <li>, …), which AdwAboutDialog takes as it is."""
    if path is None:
        return None
    try:
        release = ET.parse(path).getroot().find("releases/release")
    except (OSError, ET.ParseError):
        return None
    if release is None:
        return None
    description = release.find("description")
    if description is None:
        return None
    markup = "".join(ET.tostring(e, encoding="unicode") for e in description)
    markup = " ".join(markup.split())
    if not markup:
        return None
    return release.get("version") or "", markup


def add_to(dialog, app_id, source=None):
    """Fill "What's New" of an AdwAboutDialog from the metainfo of
    `app_id`. Returns whether there were notes."""
    notes = newest(find(app_id, source))
    if notes is None:
        return False
    version, markup = notes
    if version:
        dialog.set_release_notes_version(version)
    dialog.set_release_notes(markup)
    return True
