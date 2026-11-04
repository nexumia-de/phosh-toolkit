"""Image cache and widgets (needs a display for the widgets)."""
import gi
import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

from phosh_toolkit import tasks  # noqa: E402
from phosh_toolkit.images import ImageCache  # noqa: E402
from phosh_toolkit.testing import run_until  # noqa: E402
from phosh_toolkit.widgets import Ratio, error_page, loading_page  # noqa: E402

def _png():
    """A 1×1 PNG."""
    import struct
    import zlib

    def chunk(kind, data):
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data)))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff"))
            + chunk(b"IEND", b""))


PNG = _png()


def test_image_cache_fetches_once(tmp_path):
    fetched = []

    def fetch():
        fetched.append(1)
        return PNG

    cache = ImageCache(tmp_path / "images", tasks.run, memory=1)
    results = []
    cache.load("a-1.png", fetch, results.append)
    cache.load("a-1.png", fetch, results.append)   # waits for the first
    run_until(lambda: len(results) == 2)
    assert len(fetched) == 1 and results[0].get_width() == 1
    assert (tmp_path / "images" / "a-1.png").read_bytes() == PNG
    # Out of memory, from the disk.
    cache.load("b-1.png", fetch, results.append)
    run_until(lambda: len(results) == 3)
    cache.load("a-1.png", fetch, results.append)
    run_until(lambda: len(results) == 4)
    assert len(fetched) == 2 and results[3] is not None


def test_image_cache_reports_failure(tmp_path):
    def fetch():
        raise OSError("gone")
    cache = ImageCache(tmp_path, tasks.run)
    results = []
    cache.load("x.png", fetch, results.append)
    run_until(lambda: results)
    assert results == [None]


@pytest.fixture
def adw():
    Adw.init()


def test_ratio_height_follows_width(adw):
    ratio = Ratio(2, Gtk.Label(), natural_width=100)
    assert ratio.measure(Gtk.Orientation.VERTICAL, 300)[:2] == (150, 150)
    ratio.set_ratio(1)
    assert ratio.measure(Gtk.Orientation.VERTICAL, 300)[0] == 300
    capped = Ratio(1, Gtk.Label(), max_height=120)
    assert capped.measure(Gtk.Orientation.VERTICAL, 300)[0] == 120


def test_pages(adw):
    retried = []
    page = error_page("Offline", "No network", retry=lambda: retried.append(1))
    page.get_child().emit("clicked")
    assert retried == [1]
    assert loading_page().get_child() is not None


def test_style_row_applies_and_reports(adw):
    from phosh_toolkit import style
    manager = Adw.StyleManager.get_default()
    chosen = []
    row = style.style_row("light", chosen.append)
    assert row.get_selected() == 1
    row.set_selected(2)
    assert chosen == ["dark"]
    assert manager.get_color_scheme() == Adw.ColorScheme.FORCE_DARK
    style.apply("system")
    assert manager.get_color_scheme() == Adw.ColorScheme.DEFAULT
    assert style.color_scheme("bogus") == "DEFAULT"
