"""The route to the server: local address on a home network, remote address
elsewhere, the same server on both (phosh-toolkit
docs/shared-connection.md). No GTK."""
import logging

from gi.repository import GObject

from phosh_toolkit import network, route, tasks
from phosh_toolkit.http import AUTH, NETWORK, HttpError

log = logging.getLogger("phosh_toolkit.router")

CONNECTING = "connecting"
OFFLINE = "offline"


class Router(GObject.Object):
    """Base class of an app's connection.

    Subclasses implement:

    - `probe(url, timeout)`: blocking, in a worker thread. Ask the server
      at `url` who it is without credentials; return (server id, info).
      Raise http.HttpError when it does not answer.
    - `addresses()`: (remote URL, local URL, list of home Wi-Fi names).
    - `server_id()`: the id stored at sign-in, or "" before.

    and may override `resolved(kind, url, info)` (main loop, after a route
    was found) and `unauthorized()` (main loop, after a request answered
    401).

    `state` is "connecting", "local", "remote" or "offline"; `base_url`
    the address in use; `error` the last HttpError when offline."""

    __gsignals__ = {
        "state-changed": (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, watch=True):
        super().__init__()
        self.state = CONNECTING
        self.base_url = ""
        self.error = None
        self._resolving = []         # callbacks waiting for resolve()
        self.watcher = None
        if watch:
            self.watcher = network.Watcher()
            self.watcher.connect("changed", lambda *_: self.resolve())

    # --- for subclasses -------------------------------------------------

    def probe(self, url, timeout):
        raise NotImplementedError

    def addresses(self):
        raise NotImplementedError

    def server_id(self):
        return ""

    def resolved(self, kind, url, info):
        pass

    def unauthorized(self):
        pass

    # --- route -------------------------------------------------------

    def candidates(self, ssids):
        remote, local, home = self.addresses()
        return route.candidates(remote, local, home, ssids)

    def resolve(self, done=None):
        """Find the address to use; done(error) on the main loop."""
        self._resolving.append(done)
        if len(self._resolving) > 1:
            return
        self._set_state(CONNECTING)
        tasks.run(self._find, self._on_found)

    def _find(self):
        ssids = network.current_ssids()
        expected = self.server_id()
        error = HttpError(NETWORK, "No server address")
        for kind, url in self.candidates(ssids):
            try:
                server_id, info = self.probe(url, route.TIMEOUT[kind])
            except HttpError as e:
                log.info("%s %s: %s", kind, url, e)
                # The remote error explains more (certificate, TLS).
                if kind == route.REMOTE or error.kind == NETWORK:
                    error = e
                continue
            if expected and server_id != expected:
                # Another server at the same address: never send our
                # credentials there.
                log.warning("%s %s is server %s, not ours", kind, url, server_id)
                error = HttpError(NETWORK, "A different server answers")
                continue
            return kind, url, info
        raise error

    def _on_found(self, result, error):
        if error is None:
            kind, url, info = result
            self.base_url = url
            self.error = None
            self.resolved(kind, url, info)
            self._set_state(kind)
        else:
            self.error = error
            self._set_state(OFFLINE)
        waiting, self._resolving = self._resolving, []
        for done in waiting:
            if done:
                done(error)

    def _set_state(self, state):
        if state != self.state:
            self.state = state
            self.emit("state-changed")

    # --- calls -------------------------------------------------------

    def call(self, fn, done, *args):
        """tasks.run(fn, …) with the route resolved first, one retry
        through a new route after a network error, and unauthorized() on
        401."""
        def attempt(retry):
            def finished(result, error):
                if isinstance(error, HttpError):
                    if error.kind == AUTH:
                        self.unauthorized()
                    elif error.kind == NETWORK and retry:
                        self.resolve(lambda e: attempt(False)() if e is None
                                     else done(None, e))
                        return
                done(result, error)
            return lambda: tasks.run(fn, finished, *args)

        if not self.base_url:
            self.resolve(lambda e: attempt(True)() if e is None
                         else done(None, e))
        else:
            attempt(True)()


def probe_addresses(probe, remote_url, local_url, done):
    """Setup: ask both addresses who they are. `probe(url, timeout)` as in
    Router. done(answers, error) on the main loop with answers
    {"remote": info or HttpError, "local": …}; error only if no address
    answered or they are different servers."""
    def work():
        answers, ids = {}, set()
        for kind, url in ((route.REMOTE, remote_url), (route.LOCAL, local_url)):
            if not url:
                continue
            try:
                server_id, answers[kind] = probe(url, route.TIMEOUT[kind])
                ids.add(server_id)
            except HttpError as e:
                answers[kind] = e
        if not ids:
            # The remote error explains more (certificate, TLS).
            raise next(iter(answers.values()),
                       HttpError(NETWORK, "No server address"))
        if len(ids) > 1:
            raise HttpError(NETWORK, "The two addresses are different servers")
        return answers

    tasks.run(work, done)
