"""The Wi-Fi networks the phone is connected to, from NetworkManager on the
system bus (phosh-toolkit docs/shared-connection.md). The Flatpak needs
--system-talk-name=org.freedesktop.NetworkManager for it; without access
current_ssids() returns None and the app tries the local address first,
guarded by the server id check."""
import logging

from gi.repository import Gio, GLib, GObject

log = logging.getLogger("phosh_toolkit.network")

NM = "org.freedesktop.NetworkManager"
NM_PATH = "/org/freedesktop/NetworkManager"
PROPS = "org.freedesktop.DBus.Properties"


def _get(bus, path, interface, name):
    result = bus.call_sync(NM, path, PROPS, "Get",
                           GLib.Variant("(ss)", (interface, name)),
                           GLib.VariantType("(v)"),
                           Gio.DBusCallFlags.NONE, 2000, None)
    return result.unpack()[0]


def current_ssids(bus=None):
    """Set of SSIDs of the active Wi-Fi connections, or None."""
    try:
        bus = bus or Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        active = _get(bus, NM_PATH, NM, "ActiveConnections")
        ssids = set()
        for path in active:
            iface = NM + ".Connection.Active"
            if _get(bus, path, iface, "Type") != "802-11-wireless":
                continue
            ssid = None
            ap = _get(bus, path, iface, "SpecificObject")
            if ap and ap != "/":
                raw = _get(bus, ap, NM + ".AccessPoint", "Ssid")
                ssid = bytes(raw).decode("utf-8", "replace") if raw else None
            # The connection name is the SSID unless the user renamed it.
            ssids.add(ssid or _get(bus, path, iface, "Id"))
        return ssids
    except GLib.Error as e:
        log.info("NetworkManager not reachable: %s", e.message)
        return None


class Watcher(GObject.Object):
    """Emits "changed" (debounced) when the network may have changed.

    Two sources: GLib's network monitor, and NetworkManager's own
    PropertiesChanged on the system bus (active connections, primary
    connection, state). In the Flatpak the monitor goes through the
    network portal, which may not report a switch from Wi-Fi to mobile
    data while the network stays "available"; NetworkManager does."""
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, ())}

    # NetworkManager properties that mean "the route may be different".
    NM_PROPERTIES = ("ActiveConnections", "PrimaryConnection", "State",
                     "Connectivity")

    def __init__(self, bus=None):
        super().__init__()
        self._timeout = 0
        self._monitor = Gio.NetworkMonitor.get_default()
        self._monitor.connect("network-changed", self._on_changed)
        self._bus = None
        self._subscription = 0
        try:
            self._bus = bus or Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
            self._subscription = self._bus.signal_subscribe(
                NM, PROPS, "PropertiesChanged", NM_PATH, None,
                Gio.DBusSignalFlags.NONE, self._on_nm, None)
        except GLib.Error as e:
            log.info("NetworkManager signals not available: %s", e.message)

    def close(self):
        if self._subscription and self._bus is not None:
            self._bus.signal_unsubscribe(self._subscription)
            self._subscription = 0

    def _on_nm(self, bus, sender, path, interface, signal, parameters, *_):
        iface, changed, _invalidated = parameters.unpack()
        if iface == NM and any(name in changed for name in self.NM_PROPERTIES):
            self._on_changed()

    @property
    def available(self):
        return self._monitor.props.network_available

    def _on_changed(self, *_):
        if self._timeout:
            GLib.source_remove(self._timeout)
        self._timeout = GLib.timeout_add(1500, self._emit)

    def _emit(self):
        self._timeout = 0
        self.emit("changed")
        return GLib.SOURCE_REMOVE
