"""The "Report a Problem" dialog: the user writes a problem or an idea;
with a GitHub token it becomes an issue right away, without one GitHub's
issue form opens in the browser, filled in."""
import logging

from gi.repository import Adw, Gdk, Gtk

from phosh_toolkit import tasks
from phosh_toolkit.feedback import github
from phosh_toolkit.feedback import report as rp

log = logging.getLogger("phosh_toolkit.feedback")

# Keyring kind of the user's token.
GITHUB_TOKEN = "github-token"
TOKEN_PAGE = "https://github.com/settings/personal-access-tokens/new"

_KINDS = ((rp.PROBLEM, "Problem"), (rp.IDEA, "Idea"))
_FAILED = {
    github.NO_ACCESS: "GitHub did not accept the token. Check that it may "
                      "write issues in this repository.",
    github.OFFLINE: "GitHub cannot be reached right now.",
    github.FAILED: "GitHub did not create the issue.",
}


def launch(window, url):
    Gtk.UriLauncher.new(url).launch(window, None, None, None)


class ReportDialog(Adw.Dialog):
    """`repo` is "owner/name"; `keyring` a phosh_toolkit Keyring that
    keeps the token under GITHUB_TOKEN; `client` a phosh_toolkit http
    Client. `opener(window, url)` opens a web page (tests replace it)."""

    def __init__(self, *, repo, app_name, version, keyring, client,
                 api=github.API, environ=None, opener=launch):
        super().__init__(title="Report a Problem", content_width=480,
                         content_height=680)
        self.repo, self.version = repo, version
        self.keyring, self.client, self.api = keyring, client, api
        self.opener = opener
        self.device = rp.device(environ)
        self.issue_url = None

        self.toolbar = Adw.ToolbarView()
        self.toolbar.add_top_bar(Adw.HeaderBar())
        self.banner = Adw.Banner(button_label="Open on GitHub")
        self.banner.connect("button-clicked", lambda *_: self.open_form())
        self.toolbar.add_top_bar(self.banner)
        self.toolbar.set_content(self._form(app_name))
        self.toolbar.add_bottom_bar(self._buttons())
        self.set_child(self.toolbar)
        self._update()

    # Building

    def _form(self, app_name):
        page = Adw.PreferencesPage()
        about = Adw.PreferencesGroup(description=(
            f"Goes to the public issue list of {app_name} on GitHub. Only "
            "what you write here, the app version and the kind of device "
            "are sent."))
        self.kind_row = Adw.ComboRow(title="Kind", model=Gtk.StringList.new(
            [label for _, label in _KINDS]))
        self.kind_row.connect("notify::selected", lambda *_: self._update())
        self.title_row = Adw.EntryRow(title="Title")
        self.title_row.connect("changed", lambda *_: self._update())
        about.add(self.kind_row)
        about.add(self.title_row)
        page.add(about)

        self.text_group = Adw.PreferencesGroup()
        self.text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                 accepts_tab=False, top_margin=12,
                                 bottom_margin=12, left_margin=12,
                                 right_margin=12)
        self.text.set_size_request(-1, 160)
        self.text.get_buffer().connect("changed", lambda *_: self._update())
        frame = Gtk.Frame(child=self.text)
        self.text_group.add(frame)
        page.add(self.text_group)

        direct = Adw.PreferencesGroup(title="Send Directly", description=(
            "With a GitHub token the issue is created here. Without one, "
            "GitHub opens in the browser with everything filled in."))
        self.token_row = Adw.PasswordEntryRow(title="GitHub Token")
        self.token_row.connect("changed", lambda *_: self._update())
        self.help_row = Adw.ActionRow(
            title="Create a Token", activatable=True,
            subtitle="Fine-grained, with “Issues: Read and write” for "
                     "this app’s repository")
        self.help_row.add_suffix(Gtk.Image(
            icon_name="adw-external-link-symbolic"))
        self.help_row.connect("activated",
                              lambda *_: self.opener(self.get_root(),
                                                     TOKEN_PAGE))
        self.saved_row = Adw.ActionRow(title="Token Saved",
                                       subtitle="Kept in the keyring")
        forget = Gtk.Button(label="Forget", valign=Gtk.Align.CENTER)
        forget.add_css_class("flat")
        forget.connect("clicked", lambda *_: self.forget_token())
        self.saved_row.add_suffix(forget)
        for row in (self.token_row, self.help_row, self.saved_row):
            direct.add(row)
        page.add(direct)

        return page

    def _buttons(self):
        """Bottom bar, in thumb reach: the main action on the right."""
        bar = Gtk.Box(spacing=12, margin_top=12,
                      margin_bottom=12, margin_start=12, margin_end=12)
        self.form_button = Gtk.Button(label="Open on GitHub")
        self.form_button.connect("clicked", lambda *_: self.open_form())
        self.send_button = Gtk.Button(label="Send")
        self.send_button.connect("clicked", lambda *_: self.send())
        for button in (self.form_button, self.send_button):
            button.add_css_class("pill")
            button.set_hexpand(True)
            bar.append(button)
        return bar

    # State

    def kind(self):
        return _KINDS[self.kind_row.get_selected()][0]

    def report(self):
        buffer = self.text.get_buffer()
        text = buffer.get_text(buffer.get_start_iter(),
                               buffer.get_end_iter(), False)
        return rp.Report(self.kind(), self.title_row.get_text().strip(),
                         text.strip(), self.version, self.device)

    def saved_token(self):
        return self.keyring.lookup(GITHUB_TOKEN)

    def token(self):
        return self.saved_token() or self.token_row.get_text().strip()

    def _update(self):
        report = self.report()
        self.text_group.set_title(rp.KINDS[report.kind].heading)
        saved = bool(self.saved_token())
        self.token_row.set_visible(not saved)
        self.help_row.set_visible(not saved)
        self.saved_row.set_visible(saved)
        direct = bool(self.token())
        complete = bool(report.title and report.text)
        self.send_button.set_visible(direct)
        self.send_button.set_sensitive(complete)
        for button, main in ((self.send_button, direct),
                             (self.form_button, not direct)):
            if main:
                button.add_css_class("suggested-action")
            else:
                button.remove_css_class("suggested-action")

    def forget_token(self):
        self.keyring.clear(GITHUB_TOKEN)
        self.token_row.set_text("")
        self._update()

    # Actions

    def send(self):
        report, token = self.report(), self.token()
        if not (token and report.title and report.text):
            return
        typed = not self.saved_token()
        self.banner.set_revealed(False)
        self.send_button.set_sensitive(False)
        self.send_button.set_label("Sending…")

        def done(url, error):
            self.send_button.set_label("Send")
            if error is not None:
                reason = getattr(error, "reason", github.FAILED)
                log.warning("issue not created in %s: %s", self.repo, reason)
                self.banner.set_title(_FAILED[reason])
                self.banner.set_revealed(True)
                self._update()
                return
            log.info("issue created in %s", self.repo)
            if typed:
                self.keyring.store(GITHUB_TOKEN, token)
            self._show_sent(url)

        tasks.run(github.create_issue, done, self.client, token, self.repo,
                  report.title, rp.body(report), rp.labels(report), self.api)

    def open_form(self):
        """GitHub's issue form in the browser. When the text had to be
        shortened, the full text is on the clipboard to paste."""
        report = self.report()
        url = rp.form_url(self.repo, report)
        if report.text and len(url) >= rp.MAX_URL - 200:
            Gdk.Display.get_default().get_clipboard().set(report.text)
        self.opener(self.get_root(), url)
        self.close()

    def _show_sent(self, url):
        self.issue_url = url
        button = Gtk.Button(label="View Issue", halign=Gtk.Align.CENTER)
        button.add_css_class("pill")
        button.connect("clicked",
                       lambda *_: self.opener(self.get_root(), url))
        page = Adw.StatusPage(icon_name="emblem-ok-symbolic",
                              title="Thank You",
                              description="The issue is on GitHub.",
                              child=button)
        self.toolbar.set_content(page)
        self.toolbar.set_reveal_bottom_bars(False)
