"""The playbin player through the media proxy, with a WAV file made here."""
import io
import math
import struct
import wave

import pytest

from phosh_toolkit.http import Client
from phosh_toolkit.media import Media, init
from phosh_toolkit.proxy import MediaProxy
from phosh_toolkit.testing import run_until

gi = pytest.importorskip("gi")
gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

init()
needed = ("playbin3", "wavparse", "souphttpsrc")
missing = [e for e in needed if Gst.ElementFactory.find(e) is None]
pytestmark = pytest.mark.skipif(bool(missing), reason=f"GStreamer lacks {missing}")


def tone(seconds=2.0, rate=8000):
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(
            struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * n / rate)))
            for n in range(int(seconds * rate))))
    return out.getvalue()


@pytest.fixture
def url(server, monkeypatch):
    import conftest
    monkeypatch.setattr(conftest, "MEDIA", tone())
    http = Client("Test/1.0")
    proxy = MediaProxy(lambda path: (http, server.url + path, {}))
    yield proxy.url("/media")
    proxy.stop()


def make(url):
    media = Media(url, video=False)
    # No sound card in CI: a clocked fakesink keeps real-time playback.
    sink = Gst.ElementFactory.make("fakesink", None)
    sink.props.sync = True
    media.pipeline.props.audio_sink = sink
    return media


def test_plays_pauses_seeks_and_ends(url):
    media = make(url)
    media.play()
    run_until(lambda: media.get_timestamp() > 300_000 or media.get_error(), 15)
    assert not media.get_error()
    assert media.is_prepared() and media.get_playing()
    assert 1_900_000 < media.get_duration() < 2_100_000
    media.pause()
    run_until(lambda: not media.get_playing(), 5)
    media.seek(1_500_000)
    media.play()
    run_until(lambda: media.get_ended() or media.get_error(), 15)
    assert media.get_ended() and not media.get_error()
    assert not media.get_playing()
    media.stop()


def test_undecodable_data_is_an_error(server):
    # Without the monkeypatch /media serves bytes that are not audio.
    http = Client("Test/1.0")
    proxy = MediaProxy(lambda path: (http, server.url + path, {}))
    try:
        media = make(proxy.url("/media"))
        media.play()
        run_until(lambda: media.get_error(), 15)
        assert not media.get_playing()
        media.stop()
    finally:
        proxy.stop()
