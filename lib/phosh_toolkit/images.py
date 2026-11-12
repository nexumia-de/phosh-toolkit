"""Images from the server: cached on disk and as textures in memory."""
import hashlib
import logging
import os
import re
import shutil
from collections import OrderedDict
from pathlib import Path

from gi.repository import Gdk, GLib

log = logging.getLogger("phosh_toolkit.images")

HASHED = re.compile(r"[0-9a-f]{64}")


class ImageCache:
    """`directory` holds the files (e.g. $XDG_CACHE_HOME/<app>/images);
    `call(fn, done)` runs fn in a worker and done(result, error) on the
    main loop (router.Router.call or tasks.run). At most `memory`
    textures stay in memory. On start, a worker removes the files of
    older versions from `directory` (see remove_old_files)."""

    def __init__(self, directory, call, memory=300):
        self.directory = Path(directory)
        self.call = call
        self.memory = memory
        self._cache = OrderedDict()
        self._waiting = {}
        self.call(lambda: remove_old_files(self.directory), _cleaned)

    def load(self, name, fetch, done):
        """done(Gdk.Texture or None) on the main loop. `name` is the file
        cache key and must change when the image does (include the
        server's tag or size); the file is named after its hash, so a
        name from the server never chooses the path. `fetch()` returns the image bytes and
        runs in a worker when the file is not cached."""
        if name in self._cache:
            self._cache.move_to_end(name)
            done(self._cache[name])
            return
        if name in self._waiting:
            self._waiting[name].append(done)
            return
        self._waiting[name] = [done]
        path = self.directory / file_name(name)

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


def file_name(name):
    """The cache file of `name`: a hash, never a path the server
    controls (no "..", "/" or absolute path)."""
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def remove_old_files(directory):
    """Delete every entry of `directory` whose name is not a file_name()
    hash: the files of versions that named them after the key, which are
    never read again. Subdirectories go with their contents; symbolic
    links are removed, never followed, so nothing outside `directory` is
    touched. Returns the number of entries removed."""
    try:
        entries = list(os.scandir(directory))
    except FileNotFoundError:
        return 0
    removed = 0
    for entry in entries:
        if HASHED.fullmatch(entry.name):
            continue
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path)
            else:
                os.unlink(entry.path)
            removed += 1
        except OSError as e:
            log.info("image cache: %s", e)
    return removed


def _cleaned(removed, error):
    if error is not None:
        log.info("image cache: %s", error)
    elif removed:
        log.info("image cache: removed %d old files", removed)
