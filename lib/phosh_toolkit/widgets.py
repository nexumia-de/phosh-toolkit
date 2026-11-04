"""Small widgets every app needs: spinner, loading and error pages, and a
box of fixed aspect ratio for artwork."""
from gi.repository import Adw, Gtk


def spinner():
    if hasattr(Adw, "Spinner"):    # libadwaita 1.6
        return Adw.Spinner(width_request=32, height_request=32)
    widget = Gtk.Spinner(width_request=32, height_request=32)
    widget.start()
    return widget


def loading_page():
    page = Adw.StatusPage(vexpand=True)
    page.set_child(spinner())
    return page


def error_page(title, description, retry=None,
               icon_name="network-error-symbolic"):
    page = Adw.StatusPage(icon_name=icon_name, title=title,
                          description=description, vexpand=True)
    if retry:
        button = Gtk.Button(label="Retry", halign=Gtk.Align.CENTER)
        button.add_css_class("pill")
        button.connect("clicked", lambda *_: retry())
        page.set_child(button)
    return page


class Ratio(Gtk.Widget):
    """Gives its child the height that matches its width at a fixed aspect
    ratio (width / height), also before an image is loaded."""

    def __init__(self, ratio, child, natural_width=0, max_height=0):
        super().__init__()
        self.ratio = ratio
        # Wide windows: crop instead of growing past this (0: no limit).
        self.max_height = max_height
        self.natural_width = natural_width
        self.child = child
        child.set_parent(self)

    def set_ratio(self, ratio):
        if ratio != self.ratio:
            self.ratio = ratio
            self.queue_resize()

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            minimum = self.child.measure(orientation, -1)[0]
            return minimum, max(minimum, self.natural_width), -1, -1
        width = for_size if for_size > 0 else self.natural_width
        height = int(round(width / self.ratio))
        if self.max_height:
            height = min(height, self.max_height)
        return height, height, -1, -1

    def do_size_allocate(self, width, height, baseline):
        self.child.allocate(width, height, baseline, None)

    def do_dispose(self):
        if self.child is not None:
            self.child.unparent()
            self.child = None
