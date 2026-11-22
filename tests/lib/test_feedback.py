"""Reports as GitHub issues: body, issue form address, the REST call and
the dialog (needs a display)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import gi
import pytest

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio  # noqa: E402

from phosh_toolkit import feedback, http  # noqa: E402
from phosh_toolkit.feedback import github  # noqa: E402
from phosh_toolkit.feedback import report as rp  # noqa: E402
from phosh_toolkit.keyring import Keyring  # noqa: E402
from phosh_toolkit.testing import run_until  # noqa: E402

REPO = "nexumia-de/demo"
PROBLEM = rp.Report(rp.PROBLEM, "Map stays empty", "It shows no tiles.",
                    "1.2.0", rp.PHONE)


class FakeGitHub:
    """POST /repos/<repo>/issues: 201 with an html_url for the token
    "good", 401 without it, 404 for any other repository."""

    def __init__(self):
        self.issues = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                data = json.loads(self.rfile.read(
                    int(self.headers["Content-Length"])))
                if self.headers.get("Authorization") != "Bearer good":
                    return self._answer(401, {"message": "Bad credentials"})
                if self.path != f"/repos/{REPO}/issues":
                    return self._answer(404, {"message": "Not Found"})
                fake.issues.append((dict(self.headers), data))
                number = len(fake.issues)
                self._answer(201, {"number": number, "html_url":
                                   f"https://github.com/{REPO}/issues/{number}"})

            def _answer(self, status, data):
                body = json.dumps(data).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.api = f"http://127.0.0.1:{self.server.server_port}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def fake_github():
    fake = FakeGitHub()
    yield fake
    fake.close()


# Report

def test_device_follows_the_desktop():
    assert rp.device({"XDG_CURRENT_DESKTOP": "Phosh:GNOME"}) == rp.PHONE
    assert rp.device({"XDG_CURRENT_DESKTOP": "GNOME"}) == rp.DESKTOP
    assert rp.device({}) == rp.DESKTOP


def test_body_reads_like_the_bug_form():
    assert rp.body(PROBLEM) == (
        "### What happened\n\nIt shows no tiles.\n\n"
        "### Version\n\n1.2.0\n\n### Device\n\nPhone (Phosh)")
    assert rp.labels(PROBLEM) == ["bug"]


def test_idea_has_only_the_text():
    idea = rp.Report(rp.IDEA, "Dark map", "", "1.2.0", rp.DESKTOP)
    assert rp.body(idea) == "### What do you want to do\n\n_No response_"
    assert rp.labels(idea) == ["enhancement"]


def test_form_url_fills_the_template_fields():
    url = urlsplit(rp.form_url(REPO, PROBLEM))
    assert url.path == f"/{REPO}/issues/new"
    assert parse_qs(url.query) == {
        "template": ["bug.yml"], "title": ["Map stays empty"],
        "what": ["It shows no tiles."], "version": ["1.2.0"],
        "device": ["Phone (Phosh)"]}
    idea = rp.Report(rp.IDEA, "Dark map", "Night use", "1.2.0", rp.PHONE)
    assert parse_qs(urlsplit(rp.form_url(REPO, idea)).query) == {
        "template": ["feature.yml"], "title": ["Dark map"],
        "problem": ["Night use"]}


def test_form_url_shortens_long_text():
    long = rp.Report(rp.PROBLEM, "Long", "ä " * 6000, "1.2.0", rp.PHONE)
    url = rp.form_url(REPO, long)
    assert len(url) <= rp.MAX_URL
    assert parse_qs(urlsplit(url).query)["what"][0].endswith(
        "please paste the rest]")


def test_issue_url_for_the_about_dialog():
    query = parse_qs(urlsplit(feedback.issue_url(
        REPO, "1.2.0", {"XDG_CURRENT_DESKTOP": "GNOME"})).query)
    assert query == {"template": ["bug.yml"], "version": ["1.2.0"],
                     "device": ["Desktop"]}


# REST call

def test_create_issue_sends_title_body_and_labels(fake_github):
    client = http.Client("Test/1")
    url = github.create_issue(client, "good", REPO, "T", "B", ["bug"],
                              api=fake_github.api)
    assert url == f"https://github.com/{REPO}/issues/1"
    headers, data = fake_github.issues[0]
    assert data == {"title": "T", "body": "B", "labels": ["bug"]}
    assert headers["Accept"] == "application/vnd.github+json"
    assert headers["User-Agent"] == "Test/1"


@pytest.mark.parametrize("token,repo", [("bad", REPO), ("good", "x/y")])
def test_create_issue_without_access(fake_github, token, repo):
    with pytest.raises(github.SendError) as raised:
        github.create_issue(http.Client("Test/1"), token, repo, "T", "B",
                            [], api=fake_github.api)
    assert raised.value.reason == github.NO_ACCESS


def test_create_issue_offline():
    with pytest.raises(github.SendError) as raised:
        github.create_issue(http.Client("Test/1"), "good", REPO, "T", "B",
                            [], api="http://127.0.0.1:9")
    assert raised.value.reason == github.OFFLINE


# Dialog

@pytest.fixture
def keyring():
    return Keyring("de.nexumia.Test", {}, memory_env="PHOSH_TOOLKIT_TEST_KEYRING")


def _dialog(keyring, api, opened):
    Adw.init()
    return feedback.ReportDialog(
        repo=REPO, app_name="Demo", version="1.2.0", keyring=keyring,
        client=http.Client("Test/1"), api=api,
        environ={"XDG_CURRENT_DESKTOP": "Phosh"},
        opener=lambda window, url: opened.append(url))


def _fill(dialog, title="Map stays empty", text="It shows no tiles."):
    dialog.title_row.set_text(title)
    dialog.text.get_buffer().set_text(text)


def test_dialog_without_token_opens_the_form(keyring):
    opened = []
    dialog = _dialog(keyring, "http://127.0.0.1:9", opened)
    _fill(dialog)
    assert not dialog.send_button.get_visible()
    assert dialog.form_button.has_css_class("suggested-action")
    dialog.open_form()
    assert opened == [rp.form_url(REPO, PROBLEM)]


def test_dialog_sends_and_keeps_the_token(keyring, fake_github):
    dialog = _dialog(keyring, fake_github.api, [])
    dialog.token_row.set_text("good")
    assert dialog.send_button.get_visible()
    assert not dialog.send_button.get_sensitive()   # nothing written yet
    _fill(dialog)
    assert dialog.send_button.get_sensitive()
    dialog.send()
    run_until(lambda: dialog.issue_url is not None)
    assert dialog.issue_url == f"https://github.com/{REPO}/issues/1"
    _, data = fake_github.issues[0]
    assert data == {"title": "Map stays empty", "body": rp.body(PROBLEM),
                    "labels": ["bug"]}
    assert keyring.lookup(feedback.GITHUB_TOKEN) == "good"


def test_dialog_keeps_the_text_when_the_token_is_rejected(keyring, fake_github):
    dialog = _dialog(keyring, fake_github.api, [])
    dialog.token_row.set_text("bad")
    _fill(dialog)
    dialog.send()
    run_until(dialog.banner.get_revealed)
    assert "token" in dialog.banner.get_title()
    assert dialog.issue_url is None
    assert dialog.report() == PROBLEM
    assert keyring.lookup(feedback.GITHUB_TOKEN) is None


def test_dialog_with_saved_token_can_forget_it(keyring):
    keyring.store(feedback.GITHUB_TOKEN, "good")
    dialog = _dialog(keyring, "http://127.0.0.1:9", [])
    assert dialog.saved_row.get_visible()
    assert not dialog.token_row.get_visible()
    assert dialog.send_button.get_visible()
    dialog.forget_token()
    assert keyring.lookup(feedback.GITHUB_TOKEN) is None
    assert dialog.token_row.get_visible()
    assert not dialog.send_button.get_visible()


def test_install_adds_the_action(keyring):
    app = Adw.Application(application_id="de.nexumia.Test",
                          flags=Gio.ApplicationFlags.NON_UNIQUE)
    action = feedback.install(app, repo=REPO, app_name="Demo",
                              version="1.2.0", keyring=keyring)
    assert app.lookup_action("report-problem") is action
    assert keyring.labels[feedback.GITHUB_TOKEN] == "Demo GitHub token"
