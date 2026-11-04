"""Helpers for the apps' tests: a test PKI made with openssl for mutual TLS,
and running the GLib main loop until a condition holds."""
import ssl
import subprocess
from pathlib import Path

from gi.repository import GLib

P12_PASSWORD = "secret"


def run_until(predicate, timeout=10):
    """Iterate the default main context until predicate() is true."""
    context = GLib.MainContext.default()
    deadline = GLib.get_monotonic_time() + timeout * 1_000_000
    while not predicate():
        if GLib.get_monotonic_time() > deadline:
            raise TimeoutError("main loop condition not reached")
        context.iteration(False)
        GLib.usleep(2000)


def _openssl(*args, cwd):
    subprocess.run(["openssl", *args], cwd=cwd, check=True,
                   capture_output=True)


def make_pki(directory, client_name="Robin's phone"):
    """In `directory`: CA (ca.pem), server certificate for 127.0.0.1
    (server.pem, server.key), client certificate as PEM without key
    (client.pem), PEM with key (client-combined.pem) and as PKCS #12 with
    the password P12_PASSWORD (client.p12). Returns the directory."""
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    _openssl("req", "-x509", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
             "-nodes", "-keyout", "ca.key", "-out", "ca.pem", "-days", "2",
             "-subj", "/CN=Test CA", cwd=d)
    (d / "san.ext").write_text("subjectAltName=IP:127.0.0.1\n")
    (d / "client.ext").write_text("extendedKeyUsage=clientAuth\n")
    for name, subject, ext in (("server", "/CN=127.0.0.1", "san.ext"),
                               ("client", f"/CN={client_name}", "client.ext")):
        _openssl("req", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                 "-nodes", "-keyout", f"{name}.key", "-out", f"{name}.csr",
                 "-subj", subject, cwd=d)
        _openssl("x509", "-req", "-in", f"{name}.csr", "-CA", "ca.pem",
                 "-CAkey", "ca.key", "-CAcreateserial", "-days", "2",
                 "-extfile", ext, "-out", f"{name}.pem", cwd=d)
    (d / "client-combined.pem").write_bytes(
        (d / "client.pem").read_bytes() + (d / "client.key").read_bytes())
    _openssl("pkcs12", "-export", "-inkey", "client.key", "-in", "client.pem",
             "-out", "client.p12", "-passout", f"pass:{P12_PASSWORD}", cwd=d)
    return d


def server_context(pki):
    """ssl.SSLContext for a test server that requires a client certificate
    signed by the test CA."""
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(pki / "server.pem", pki / "server.key")
    context.load_verify_locations(pki / "ca.pem")
    context.verify_mode = ssl.CERT_REQUIRED
    return context
