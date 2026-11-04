"""Secrets in the keyring (libsecret; in the Flatpak through the Secret
portal). Without libsecret or a keyring daemon they are kept in memory
for the session. No GTK."""
import logging
import os

log = logging.getLogger("phosh_toolkit.keyring")

# The password of a PKCS #12 client certificate (certificate.py).
CERTIFICATE_PASSWORD = "certificate-password"


class Keyring:
    """Secrets of one app, one per `kind`.

    `schema` is the app id, `labels` maps every kind to the label the
    keyring shows (e.g. {"token": "MyApp access token"}). When the
    environment variable `memory_env` is "memory" (tests, screenshots),
    nothing touches the real keyring."""

    def __init__(self, schema, labels, memory_env=None):
        self.schema_name = schema
        self.labels = dict(labels)
        self.memory_env = memory_env
        self._memory = {}
        self._schema = None

    def _secret(self):
        if self.memory_env and os.environ.get(self.memory_env) == "memory":
            return None
        try:
            import gi
            gi.require_version("Secret", "1")
            from gi.repository import Secret
        except (ImportError, ValueError):
            log.warning("libsecret not available, secrets are kept in memory")
            return None
        if self._schema is None:
            self._schema = Secret.Schema.new(
                self.schema_name, Secret.SchemaFlags.NONE,
                {"kind": Secret.SchemaAttributeType.STRING})
        return Secret

    def store(self, kind, value):
        Secret = self._secret()
        if Secret is None:
            self._memory[kind] = value
            return
        try:
            Secret.password_store_sync(self._schema, {"kind": kind},
                                       Secret.COLLECTION_DEFAULT,
                                       self.labels.get(kind, kind), value, None)
        except Exception as e:  # GLib.Error: no keyring daemon, locked, …
            log.warning("keyring: %s; keeping %s in memory", e, kind)
            self._memory[kind] = value

    def lookup(self, kind):
        if kind in self._memory:
            return self._memory[kind]
        Secret = self._secret()
        if Secret is None:
            return None
        try:
            return Secret.password_lookup_sync(self._schema, {"kind": kind}, None)
        except Exception as e:
            log.warning("keyring: %s", e)
            return None

    def clear(self, kind):
        self._memory.pop(kind, None)
        Secret = self._secret()
        if Secret is None:
            return
        try:
            Secret.password_clear_sync(self._schema, {"kind": kind}, None)
        except Exception as e:
            log.warning("keyring: %s", e)

    def forget_memory(self):
        """Drop the secrets kept in memory (between tests)."""
        self._memory.clear()
