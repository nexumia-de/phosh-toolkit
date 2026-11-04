"""The playbin player through the media proxy, with a WAV file made here."""
import io
import math
import struct
import threading
import wave
from pathlib import Path

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
# tracks.mkv (made with ffmpeg's smptebars and sine): 30 s VP8 video,
# English and German Vorbis audio, an embedded English SRT subtitle.
TRACKS = Path(__file__).resolve().parent / "data" / "tracks.mkv"
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


def test_playback_moves_to_the_new_route(server, monkeypatch):
    """The route changes mid-song (Wi-Fi gone): reroute() cuts the stream,
    GStreamer's HTTP source reconnects with a Range and the song goes on
    from the other address."""
    import conftest
    from conftest import FakeServer
    monkeypatch.setattr(conftest, "MEDIA", tone(seconds=20.0))
    # Served a little faster than it plays (16 kB/s), so GStreamer is
    # still reading when the route changes.
    server.media_rate = 24000
    other = FakeServer("server-b").start()
    http = Client("Test/1.0")
    current = {"url": server.url}
    proxy = MediaProxy(lambda path: (http, current["url"] + path, {}))
    try:
        media = make(proxy.url("/media"))
        media.play()
        run_until(lambda: media.get_timestamp() > 1_000_000 or media.get_error(), 15)
        assert not media.get_error()
        current["url"] = other.url
        proxy.reroute()
        run_until(lambda: any(p == "/media" for m, p, h in other.requests)
                  or media.get_error(), 15)
        before = media.get_timestamp()
        run_until(lambda: media.get_timestamp() > before + 1_000_000
                  or media.get_error(), 15)
        assert not media.get_error() and media.get_playing()
        ranges = [h.get("Range") for m, p, h in other.requests if p == "/media"]
        assert ranges and ranges[0] and not ranges[0].startswith("bytes=0-")
        media.stop()
    finally:
        proxy.stop()
        other.stop()


def test_stop_releases_the_pipeline_on_the_main_thread(url):
    # gtk4paintablesink aborts the process when it is freed on another
    # thread; Python's garbage collector may run on a proxy thread, so
    # stop() leaves nothing of the pipeline behind.
    media = make(url)
    media.play()
    run_until(lambda: media.is_prepared() or media.get_error(), 15)
    media.stop()
    assert media.pipeline is None and media.paintable is None
    media.seek(0)
    media.set_playing(True)
    holder = [media]
    del media
    thread = threading.Thread(target=holder.clear)
    thread.start()
    thread.join()


@pytest.mark.skipif(any(Gst.ElementFactory.find(e) is None
                        for e in ("matroskademux", "vorbisdec")),
                    reason="GStreamer lacks Matroska or Vorbis")
def test_chosen_audio_track_and_no_subtitle():
    media = Media(TRACKS.as_uri(), video=False, audio_position=1)
    media.pipeline.props.audio_sink = Gst.ElementFactory.make("fakesink", None)
    selected = []

    def on_message(bus, message):
        if message.type == Gst.MessageType.STREAMS_SELECTED:
            selected[:] = [message.streams_selected_get_stream(i)
                           for i in range(message.streams_selected_get_size())]

    def chosen():
        audio = [s.get_tags().get_string("language-code")[1] for s in selected
                 if s.get_stream_type() & Gst.StreamType.AUDIO]
        texts = [s for s in selected if s.get_stream_type() & Gst.StreamType.TEXT]
        return audio, len(texts)

    media.pipeline.get_bus().connect("message", on_message)
    try:
        media.play()
        # playbin3 first announces its own choice (English and the
        # embedded subtitle), then the chosen one.
        run_until(lambda: chosen() == (["de"], 0) or media.get_error(), 15)
        assert not media.get_error()
        # Switching needs no restart.
        media.select_audio(0)
        run_until(lambda: chosen() == (["en"], 0) or media.get_error(), 15)
        assert not media.get_error()
        assert media.position_now() > 0
    finally:
        media.stop()
