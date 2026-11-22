"""The location portal wrapper against a stand-in portal (CI has no
GeoClue and nobody to answer the permission dialog)."""
import pytest
from gi.repository import GLib

from phosh_toolkit import location  # noqa: I001 (sets the Xdp version)
from gi.repository import Xdp  # noqa: E402


class FakePortal:
    def __init__(self, answer=True):
        self.answer = answer      # True, False or a GLib.Error
        self.started = []
        self.stopped = 0
        self.handlers = {}

    def connect(self, signal, handler):
        self.handlers[signal] = handler

    def location_monitor_start(self, parent, distance, time, accuracy,
                               flags, cancellable, callback):
        self.started.append((parent, distance, time, accuracy, flags))
        self.callback = callback

    def location_monitor_start_finish(self, result):
        if isinstance(self.answer, GLib.Error):
            raise self.answer
        return self.answer

    def location_monitor_stop(self):
        self.stopped += 1

    def fix(self, latitude, longitude, accuracy):
        self.handlers["location-updated"](
            self, latitude, longitude, 0.0, accuracy, 0.0, 0.0, "", 0, 0)


def make(portal, distance_m=200, **kwargs):
    loc = location.Location(distance_m, **kwargs)
    loc._new_portal = lambda: portal
    loc._parent = lambda window: window
    seen = {"changed": [], "failed": []}
    loc.connect("changed", lambda _l, *fix: seen["changed"].append(fix))
    loc.connect("failed", lambda _l, message: seen["failed"].append(message))
    return loc, seen


def test_distance_and_accuracy_reach_the_portal():
    portal = FakePortal()
    loc, _ = make(portal, 35, accuracy=Xdp.LocationAccuracy.STREET)
    loc.start("window")
    assert portal.started == [("window", 35, 0, Xdp.LocationAccuracy.STREET,
                               Xdp.LocationMonitorFlags.NONE)]


def test_exact_accuracy_by_default():
    portal = FakePortal()
    loc, _ = make(portal)
    loc.start("window")
    assert portal.started[0][1:4] == (200, 0, Xdp.LocationAccuracy.EXACT)


def test_fixes_are_kept_and_emitted():
    portal = FakePortal()
    loc, seen = make(portal)
    loc.start("window")
    portal.callback(portal, None)
    assert loc.running and loc.fix is None
    portal.fix(52.5, 13.4, 12.0)
    assert loc.fix == (52.5, 13.4, 12.0)
    assert seen == {"changed": [(52.5, 13.4, 12.0)], "failed": []}


def test_start_twice_asks_once_and_stop_stops():
    portal = FakePortal()
    loc, _ = make(portal)
    loc.start("window")
    loc.start("window")
    assert len(portal.started) == 1
    loc.stop()
    loc.stop()
    assert portal.stopped == 1 and not loc.running
    loc.start("window")
    assert len(portal.started) == 2


@pytest.mark.parametrize("answer, message", [
    (False, "The location portal refused"),
    (GLib.Error("Location access denied"), "Location access denied"),
])
def test_refusal_fails_and_allows_another_try(answer, message):
    portal = FakePortal(answer)
    loc, seen = make(portal)
    loc.start("window")
    portal.callback(portal, None)
    assert seen["failed"] == [message] and not loc.running
    loc.start("window")
    assert len(portal.started) == 2


def test_no_portal_fails():
    loc, seen = make(None)

    def no_portal():
        raise GLib.Error("no portal")
    loc._new_portal = no_portal
    loc.start("window")
    assert seen["failed"] == ["no portal"] and not loc.running
