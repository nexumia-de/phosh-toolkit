"""The client certificate the user picked: a private copy in the app's data
directory, its PKCS #12 password in the keyring
(phosh-toolkit docs/shared-connection.md). No GTK."""
import os
from pathlib import Path

from phosh_toolkit import tls
from phosh_toolkit.keyring import CERTIFICATE_PASSWORD


class CertificateFile:
    """`path` is e.g. $XDG_DATA_HOME/<app>/client-certificate; `keyring` a
    keyring.Keyring with a label for CERTIFICATE_PASSWORD."""

    def __init__(self, path, keyring):
        self.path = Path(path)
        self.keyring = keyring

    def save(self, data, password=""):
        """Keep a private copy (mode 600) of the file the user picked, so the
        app does not depend on the original staying where it was."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        tmp.replace(self.path)
        if password:
            self.keyring.store(CERTIFICATE_PASSWORD, password)
        else:
            self.keyring.clear(CERTIFICATE_PASSWORD)

    def delete(self):
        self.path.unlink(missing_ok=True)
        self.keyring.clear(CERTIFICATE_PASSWORD)

    def load(self):
        """The saved Gio.TlsCertificate. Raises OSError or
        tls.CertificateError."""
        return tls.load(self.path.read_bytes(),
                        self.keyring.lookup(CERTIFICATE_PASSWORD))

    def describe(self):
        """One line for the certificate row: whose it is and until when, or
        why it can't be used."""
        try:
            cert = self.load()
        except (OSError, tls.CertificateError) as e:
            return f"Can't be used: {e}"
        subject, expires = tls.describe(cert)
        if expires is not None:
            return f"{subject}, valid until {expires.format('%x')}"
        return subject
