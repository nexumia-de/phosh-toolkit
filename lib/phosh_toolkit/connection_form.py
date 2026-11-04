"""Where the server is: its address, the client certificate and the home
network (phosh-toolkit docs/shared-connection.md). The same groups serve
the first-run setup page and the "Connection" page of the preferences."""
from gi.repository import Adw, Gio, GLib, Gtk

from phosh_toolkit import network, proxy_login, route, tls
from phosh_toolkit.http import (AUTH, CERTIFICATE_REQUIRED, PROXY_LOGIN, Client,
                                HttpError, origin)
from phosh_toolkit.router import probe_addresses


def describe_error(error):
    """One sentence for a toast."""
    if isinstance(error, HttpError):
        if error.kind == CERTIFICATE_REQUIRED:
            return "The server asks for a client certificate. Choose yours above."
        if error.kind == AUTH:
            return "Wrong user name or password"
        if error.kind == PROXY_LOGIN:
            return "The proxy in front of the server asks for its own login"
        return str(error)
    return str(error) or "Something went wrong"


class ConnectionForm:
    """Groups for the remote address, client certificate and home network,
    filled from and saved to an account.

    - `account` has `remote_url`, `local_url`, `home_networks` (list) and
      `certificate` (bool: a certificate is saved).
    - `certificates` is a certificate.CertificateFile.
    - `probe(http)` returns a callable(url, timeout) -> (server id, info)
      that asks the server through the http.Client `http` (see
      router.Router.probe).
    - `user_agent` is used for the probe's http.Client.
    - `server_description` and `home_description` are the group
      descriptions, e.g. "The address you use to reach MyServer from
      anywhere"."""

    def __init__(self, window, account, certificates, probe, user_agent, *,
                 server_description, home_description, toast=None):
        self.window = window
        self.certificates = certificates
        self.probe = probe
        self.user_agent = user_agent
        # Errors appear where the form is: the window or the preferences.
        self.toast = toast or window.toast
        self.certificate_data = None     # newly chosen file
        self.has_certificate = account.certificate
        self.networks = list(account.home_networks)
        # Proxy login (proxy_login.py): the stored cookies, plus new ones
        # from a login in this form, saved by apply().
        self.cookies = proxy_login.CookieJar(certificates.keyring)
        self.proxy_cookies = self.cookies.load()
        # Tests: (Gio.TlsCertificate, host) pairs the login view trusts.
        self.trusted = ()

        self.server = Adw.PreferencesGroup(title="Server",
                                           description=server_description)
        self.remote = Adw.EntryRow(title="Server Address",
                                   text=account.remote_url,
                                   input_purpose=Gtk.InputPurpose.URL)
        self.server.add(self.remote)
        self.cert_row = Adw.ActionRow(title="Client Certificate")
        choose = Gtk.Button(label="Choose…", valign=Gtk.Align.CENTER)
        choose.add_css_class("flat")
        choose.connect("clicked", self._on_choose)
        self.cert_remove = Gtk.Button(icon_name="user-trash-symbolic",
                                      valign=Gtk.Align.CENTER,
                                      tooltip_text="Remove Certificate")
        self.cert_remove.add_css_class("flat")
        self.cert_remove.update_property([Gtk.AccessibleProperty.LABEL],
                                         ["Remove Certificate"])
        self.cert_remove.connect("clicked", self._on_remove_certificate)
        self.cert_row.add_suffix(self.cert_remove)
        self.cert_row.add_suffix(choose)
        self.server.add(self.cert_row)
        self.password = Adw.PasswordEntryRow(title="Certificate Password")
        self.server.add(self.password)

        self.home = Adw.PreferencesGroup(title="Home Network",
                                         description=home_description)
        self.local = Adw.EntryRow(title="Local Address", text=account.local_url,
                                  input_purpose=Gtk.InputPurpose.URL)
        self.home.add(self.local)
        self.network_rows = []
        self.add_current = Adw.ActionRow(title="Add Current Wi-Fi",
                                         activatable=True)
        self.add_current.add_prefix(Gtk.Image(icon_name="list-add-symbolic"))
        self.add_current.connect("activated", self._on_add_current)
        self.home.add(self.add_current)
        self.add_named = Adw.EntryRow(title="Add Wi-Fi by Name",
                                      show_apply_button=True)
        self.add_named.connect("apply", self._on_add_named)
        self.home.add(self.add_named)
        self._refresh_certificate(account.certificate and certificates.describe())
        self._refresh_networks()
        self._current_ssids = network.current_ssids()
        self._refresh_current()

    @property
    def groups(self):
        return [self.server, self.home]

    # --- certificate ---------------------------------------------------

    def _refresh_certificate(self, subtitle=None):
        has = self.has_certificate or self.certificate_data is not None
        self.cert_row.set_subtitle(GLib.markup_escape_text(
            subtitle or ("Chosen" if has else
                         "None, only needed if the server asks for one")))
        self.cert_remove.set_visible(has)
        needs_password = (self.certificate_data is not None
                          and not tls.is_pem(self.certificate_data))
        self.password.set_visible(needs_password)

    def _on_choose(self, *_):
        dialog = Gtk.FileDialog(title="Choose Client Certificate")
        certs = Gtk.FileFilter(name="Certificates (.p12, .pfx, .pem)")
        for pattern in ("*.p12", "*.pfx", "*.pem", "*.crt"):
            certs.add_pattern(pattern)
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(certs)
        dialog.set_filters(filters)
        dialog.open(self.window, None, self._on_chosen)

    def _on_chosen(self, dialog, result):
        try:
            file = dialog.open_finish(result)
        except GLib.Error:
            return  # cancelled
        try:
            data = file.load_bytes(None)[0].get_data()
        except GLib.Error as e:
            self.toast(e.message)
            return
        self.choose_data(data, file.get_basename())

    def choose_data(self, data, name):
        """Use the certificate file `data` (also for tests)."""
        self.certificate_data = data
        self.cert_row.remove_css_class("error")
        self._refresh_certificate(name)
        if self.password.get_visible():
            self.password.grab_focus()

    def _on_remove_certificate(self, *_):
        self.certificate_data = None
        self.has_certificate = False
        self.password.set_text("")
        self._refresh_certificate()

    def certificate(self):
        """The chosen Gio.TlsCertificate, the saved one, or None. Raises
        tls.CertificateError or OSError."""
        if self.certificate_data is not None:
            return tls.load(self.certificate_data, self.password.get_text())
        if self.has_certificate:
            return self.certificates.load()
        return None

    # --- home networks ---------------------------------------------------

    def _refresh_networks(self):
        for row in self.network_rows:
            self.home.remove(row)
        self.network_rows = []
        for ssid in self.networks:
            row = Adw.ActionRow(title=GLib.markup_escape_text(ssid))
            row.add_prefix(Gtk.Image(icon_name="network-wireless-symbolic"))
            remove = Gtk.Button(icon_name="list-remove-symbolic",
                                valign=Gtk.Align.CENTER,
                                tooltip_text="Remove Network")
            remove.add_css_class("flat")
            remove.update_property([Gtk.AccessibleProperty.LABEL],
                                   [f"Remove {ssid}"])
            remove.connect("clicked", self._on_remove_network, ssid)
            row.add_suffix(remove)
            self.home.add(row)
            self.network_rows.append(row)
        # Keep the add rows last.
        for row in (self.add_current, self.add_named):
            self.home.remove(row)
            self.home.add(row)

    def _refresh_current(self):
        ssids = sorted((self._current_ssids or set()) - set(self.networks))
        self.add_current.set_sensitive(bool(ssids))
        self.add_current.set_subtitle(
            GLib.markup_escape_text(", ".join(ssids)) if ssids else
            "Not connected to a Wi-Fi network" if self._current_ssids is not None
            else "Wi-Fi name not available")

    def _add(self, ssid):
        ssid = ssid.strip()
        if ssid and ssid not in self.networks:
            self.networks.append(ssid)
            self._refresh_networks()
            self._refresh_current()

    def _on_add_current(self, *_):
        for ssid in sorted((self._current_ssids or set()) - set(self.networks)):
            self._add(ssid)

    def _on_add_named(self, row):
        self._add(row.get_text())
        row.set_text("")

    def _on_remove_network(self, button, ssid):
        self.networks.remove(ssid)
        self._refresh_networks()
        self._refresh_current()

    # --- values ------------------------------------------------------------

    def addresses(self):
        """(remote, local) normalized; raises route.AddressError with the
        offending row marked."""
        values = []
        for row in (self.remote, self.local):
            row.remove_css_class("error")
            text = row.get_text().strip()
            if not text:
                values.append("")
                continue
            try:
                url = route.normalize(text)
            except route.AddressError:
                row.add_css_class("error")
                raise
            # Show what is used, e.g. with the added "https://".
            if url != text:
                row.set_text(url)
            values.append(url)
        if not any(values):
            self.remote.add_css_class("error")
            raise route.AddressError("Enter the server address")
        return tuple(values)

    def apply(self, account):
        """Write the form into `account` and keep the certificate."""
        account.remote_url, account.local_url = self.addresses()
        account.home_networks = list(self.networks)
        self.cookies.save(self.proxy_cookies)
        if self.certificate_data is not None:
            self.certificates.save(self.certificate_data,
                                   self.password.get_text())
            account.certificate = True
        elif not self.has_certificate:
            self.certificates.delete()
            account.certificate = False

    def check(self, done):
        """Validate, load the certificate and ask the server(s).
        done(answers, http) on success (see router.probe_addresses), or
        done(None, None) after an error shown as a toast. Returns False
        when nothing was sent."""
        try:
            remote, local = self.addresses()
            certificate = self.certificate()
        except route.AddressError as e:
            self.toast(str(e))
            return False
        except tls.PasswordNeeded as e:
            self.password.add_css_class("error")
            self.password.set_visible(True)
            self.toast(str(e))
            return False
        except (tls.CertificateError, OSError) as e:
            self.cert_row.add_css_class("error")
            self.toast(str(e))
            return False
        self.password.remove_css_class("error")
        http = Client(self.user_agent)
        http.certificate = certificate
        http.cookies = dict(self.proxy_cookies)

        def probed(answers, error):
            if getattr(error, "kind", None) == PROXY_LOGIN and \
                    self._proxy_login(error, http, remote or local, done):
                return
            if error is not None:
                if getattr(error, "kind", None) == CERTIFICATE_REQUIRED:
                    self.cert_row.add_css_class("error")
                self.toast(describe_error(error))
                done(None, None)
                return
            local_answer = answers.get(route.LOCAL)
            if isinstance(local_answer, HttpError) and route.REMOTE in answers:
                self.toast("The local address does not answer from "
                           "here; it is tried again at home")
            done(answers, http)

        probe_addresses(self.probe(http), remote, local, probed)
        return True

    def _proxy_login(self, error, http, server, done):
        """Show the proxy's login page; afterwards check() again. False if
        it can't be shown."""
        nav = getattr(self.window, "nav", None)
        if nav is None or not proxy_login.available():
            return False

        state = {"signed_in": False}

        def signed_in(cookies):
            state["signed_in"] = True
            self.proxy_cookies[origin(server)] = cookies
            nav.pop()
            if not self.check(done):
                done(None, None)

        def hidden(page):
            # Swiped back without signing in.
            if not state["signed_in"] and page.get_parent() is None:
                done(None, None)

        self.toast(describe_error(error))
        page = proxy_login.make_page(
            server, error.url or server, http,
            lambda client, url, timeout: self.probe(client)(url, timeout),
            signed_in, self.trusted)
        page.connect("hidden", hidden)
        nav.push(page)
        return True

    def reachable_url(self, answers):
        """The address that answered, local preferred, after check()."""
        remote, local = self.addresses()
        answer = answers.get(route.LOCAL)
        return local if answer is not None and not isinstance(answer, HttpError) \
            else remote

    def answer(self, answers):
        """The server info of the address that answered."""
        return next(a for a in answers.values() if not isinstance(a, HttpError))
