#!/usr/bin/env python3
"""Tiny adaptive libadwaita demo used to verify scripts/screenshot.sh.

Shows an AdwNavigationSplitView that collapses into a single pane below
400 sp via AdwBreakpoint, which is the pattern every app should follow.
"""
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: E402

ITEMS = ["Inbox", "Starred", "Sent", "Drafts", "Archive"]


class DemoWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Phosh Demo")
        self.set_default_size(360, 720)
        self.set_size_request(360, 294)

        sidebar_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        for name in ITEMS:
            sidebar_list.append(Adw.ActionRow(title=name, activatable=True))

        sidebar_view = Adw.ToolbarView(content=Gtk.ScrolledWindow(
            child=sidebar_list, hscrollbar_policy=Gtk.PolicyType.NEVER))
        sidebar_view.add_top_bar(Adw.HeaderBar())
        sidebar = Adw.NavigationPage(title="Folders", child=sidebar_view)

        status = Adw.StatusPage(
            icon_name="phone-symbolic",
            title="Hello, Phosh",
            description="Adaptive GTK4 + libadwaita at 360×720.",
        )
        content_view = Adw.ToolbarView(content=status)
        content_view.add_top_bar(Adw.HeaderBar())
        content = Adw.NavigationPage(title="Inbox", child=content_view)

        split = Adw.NavigationSplitView(sidebar=sidebar, content=content)
        split.set_show_content(True)
        self.set_content(split)

        bp = Adw.Breakpoint.new(Adw.BreakpointCondition.parse("max-width: 400sp"))
        bp.add_setter(split, "collapsed", True)
        self.add_breakpoint(bp)

        sidebar_list.connect("row-activated", lambda *_: split.set_show_content(True))


class DemoApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.github.suitably.PhoshDemo")

    def do_activate(self):
        (self.props.active_window or DemoWindow(self)).present()


if __name__ == "__main__":
    sys.exit(DemoApp().run(sys.argv))
