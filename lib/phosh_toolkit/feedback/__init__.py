"""Report a problem or an idea from inside the app, as a GitHub issue
(docs/feedback.md). install() adds the action `app.report-problem`."""
from gi.repository import Gio

from phosh_toolkit import http
from phosh_toolkit.feedback import report as rp
from phosh_toolkit.feedback.dialog import GITHUB_TOKEN, ReportDialog
from phosh_toolkit.keyring import Keyring

__all__ = ["GITHUB_TOKEN", "ReportDialog", "install", "issue_url"]

TEST_KEYRING = "PHOSH_TOOLKIT_TEST_KEYRING"


def install(app, *, repo, app_name, version, keyring=None, client=None):
    """Add `app.report-problem` to the Gtk.Application `app`; it opens the
    dialog over the active window. `repo` is "owner/name". Without a
    `keyring` the token is kept under the app id; without a `client` one
    is made with the app's User-Agent. Returns the action."""
    if keyring is None:
        keyring = Keyring(app.get_application_id(), {},
                          memory_env=TEST_KEYRING)
    keyring.labels.setdefault(GITHUB_TOKEN, f"{app_name} GitHub token")
    if client is None:
        client = http.Client(
            f"{app_name}/{version} (+https://github.com/{repo})")

    def activate(*_):
        ReportDialog(repo=repo, app_name=app_name, version=version,
                     keyring=keyring, client=client).present(
            app.get_active_window())

    action = Gio.SimpleAction.new("report-problem", None)
    action.connect("activate", activate)
    app.add_action(action)
    return action


def issue_url(repo, version, environ=None):
    """The repository's bug form with version and device filled in: for
    AdwAboutDialog's `issue-url`."""
    return rp.form_url(repo, rp.Report(rp.PROBLEM, "", "", version,
                                       rp.device(environ)))
