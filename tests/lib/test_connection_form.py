"""The connection form with real widgets (needs a display; CI runs it under
xvfb-run)."""
import json
from types import SimpleNamespace

import gi
import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw  # noqa: E402

from phosh_toolkit import connection_form  # noqa: E402
from phosh_toolkit.certificate import CertificateFile  # noqa: E402
from phosh_toolkit.http import HttpError  # noqa: E402
from phosh_toolkit.keyring import CERTIFICATE_PASSWORD, Keyring  # noqa: E402
from phosh_toolkit.route import LOCAL, REMOTE  # noqa: E402
from phosh_toolkit.testing import P12_PASSWORD, run_until  # noqa: E402


@pytest.fixture
def form(tmp_path, monkeypatch, trust):
    Adw.init()
    monkeypatch.setattr(connection_form.network, "current_ssids", lambda: {"Home"})
    keyring = Keyring("de.nexumia.Test", {}, memory_env="PHOSH_TOOLKIT_TEST_KEYRING")
    toasts = []
    window = SimpleNamespace(toast=toasts.append)
    account = SimpleNamespace(remote_url="", local_url="", home_networks=[],
                              certificate=False)

    def probe(http):
        http.tls_database = trust

        def ask(url, timeout):
            answer = json.loads(http.request("GET", url + "/info",
                                             timeout=timeout).body)
            return answer["id"], answer
        return ask

    f = connection_form.ConnectionForm(
        window, account, CertificateFile(tmp_path / "cert", keyring), probe,
        "Test/1.0", server_description="Where", home_description="Home")
    f.toasts, f.account, f.keyring = toasts, account, keyring
    yield f
    keyring.forget_memory()


def check(form):
    done = []
    assert form.check(lambda answers, http: done.append((answers, http)))
    run_until(lambda: done)
    return done[0]


def test_address_is_normalized_and_required(form):
    assert not form.check(lambda *a: None)
    assert form.remote.has_css_class("error")
    form.remote.set_text("media.example.org/")
    assert form.addresses() == ("https://media.example.org", "")
    assert form.remote.get_text() == "https://media.example.org"


def test_current_wifi_is_offered(form):
    assert form.add_current.get_sensitive()
    form._on_add_current()
    assert form.networks == ["Home"] and not form.add_current.get_sensitive()


def test_certificate_is_asked_for_and_kept(form, mtls_server, pki):
    form.remote.set_text(mtls_server.url)
    form.local.set_text("http://127.0.0.1:9")
    assert check(form) == (None, None)
    assert form.cert_row.has_css_class("error")
    assert "client certificate" in form.toasts[-1]
    form.choose_data((pki / "client.p12").read_bytes(), "client.p12")
    assert form.password.get_visible()
    form.password.set_text(P12_PASSWORD)
    answers, http = check(form)
    assert answers[REMOTE] == {"id": "server-a"}
    assert isinstance(answers[LOCAL], HttpError)
    assert "tried again at home" in form.toasts[-1]
    assert form.reachable_url(answers) == mtls_server.url
    assert form.answer(answers) == {"id": "server-a"}
    assert http.certificate is not None
    form.apply(form.account)
    assert form.account.certificate and form.certificates.path.exists()
    assert form.keyring.lookup(CERTIFICATE_PASSWORD) == P12_PASSWORD
    form._on_remove_certificate()
    form.apply(form.account)
    assert not form.account.certificate and not form.certificates.path.exists()


def test_wrong_certificate_password(form, mtls_server, pki):
    form.remote.set_text(mtls_server.url)
    form.choose_data((pki / "client.p12").read_bytes(), "client.p12")
    form.password.set_text("nope")
    assert not form.check(lambda *a: None)
    assert form.password.has_css_class("error")
