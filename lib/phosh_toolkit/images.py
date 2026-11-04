"""Images from the server: cached on disk and as textures in memory."""
import logging
from collections import OrderedDict
from pathlib import Path

from gi.repository import Gdk, GLib

log = logging.getLogger("phosh_toolkit.images")


class ImageCache:
    """`directory` holds the files (e.g. $XDG_CACHE_HOME/<app>/images);
    `call(fn, done)` runs fn in a worker and done(result, error) on the
    main loop (router.Router.call or tasks.run). At most `memory`
    textures stay in memory."""

    def __init__(self, directory, call, memory=300):
        self.directory = Path(directory)
        self.call = call
        self.memory = memory
        self._cache = OrderedDict()
        self._waiting = {}

    def load(self, name, fetch, done):
        """done(Gdk.Texture or None) on the main loop. `name` is the file
        name in the cache and must change when the image does (include
        the server's tag or size); `fetch()` returns the image bytes and
        runs in a worker when the file is not cached."""
        if name in self._cache:
            self._cache.move_to_end(name)
            done(self._cache[name])
            return
        if name in self._waiting:
            self._waiting[name].append(done)
            return
        self._waiting[name] = [done]
        path = self.directory / name

        def work():
            try:
                data = path.read_bytes()
            except OSError:
                data = fetch()
                try:
                    self.directory.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
                except OSError as e:
                    log.info("image cache: %s", e)
            return Gdk.Texture.new_from_bytes(GLib.Bytes.new(data))

        def finished(texture, error):
            if error is not None:
                log.debug("image %s: %s", name, error)
                texture = None
            else:
                self._cache[name] = texture
                while len(self._cache) > self.memory:
                    self._cache.popitem(last=False)
            for callback in self._waiting.pop(name, []):
                callback(texture)

        self.call(work, finished)
